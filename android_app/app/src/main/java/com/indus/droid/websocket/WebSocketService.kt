package com.indus.droid.websocket

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.Base64
import androidx.core.app.NotificationCompat
import com.indus.droid.MainActivity
import com.indus.droid.accessibility.AccessibilityService
import com.indus.droid.model.*
import com.indus.droid.notification.NotificationListenerService
import io.ktor.client.*
import io.ktor.client.engine.cio.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.plugins.logging.*
import io.ktor.client.request.*
import io.ktor.client.statement.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.coroutines.*
import kotlinx.serialization.json.Json
import timber.log.Timber
import java.net.URI

class WebSocketService : Service() {

    companion object {
        const val CHANNEL_ID = "indus_websocket_channel"
        const val NOTIFICATION_ID = 1001
        
        const val ACTION_ACCESSIBILITY_READY = "com.indus.droid.ACCESSIBILITY_READY"
        const val ACTION_NOTIFICATION_LISTENER_READY = "com.indus.droid.NOTIFICATION_LISTENER_READY"
        const val ACTION_NEW_NOTIFICATION = "com.indus.droid.NEW_NOTIFICATION"
        const val ACTION_SEND_REQUEST = "com.indus.droid.SEND_REQUEST"
        const val ACTION_SEND_RESPONSE = "com.indus.droid.SEND_RESPONSE"
        
        const val PREFS_NAME = "indus_prefs"
        const val KEY_SERVER_HOST = "server_host"
        const val KEY_SERVER_PORT = "server_port"
        const val KEY_DEVICE_ID = "device_id"
        const val KEY_DEVICE_NAME = "device_name"
        const val KEY_PAIRED = "paired"
        const val KEY_AUTO_START = "auto_start"
    }

    private var client: HttpClient? = null
    private var webSocketSession: DefaultClientWebSocketSession? = null
    private var messageId = 0
    private val pendingRequests = mutableMapOf<Int, CompletableDeferred<WsMessage>>()
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val handler = Handler(Looper.getMainLooper())
    private val reconnectJob = SupervisorJob()
    private val reconnectScope = CoroutineScope(Dispatchers.IO + reconnectJob)
    private var isConnected = false
    private var serverHost = "10.0.2.2"  // Default for emulator
    private var serverPort = 8765
    private var deviceId = ""
    private var deviceName = ""
    private var paired = false
    
    private val json = Json { ignoreUnknownKeys = true }

    override fun onCreate() {
        super.onCreate()
        loadPrefs()
        initDeviceId()
        initHttpClient()
        registerReceivers()
        createNotificationChannel()
    }

    private fun loadPrefs() {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        serverHost = prefs.getString(KEY_SERVER_HOST, "10.0.2.2") ?: "10.0.2.2"
        serverPort = prefs.getInt(KEY_SERVER_PORT, 8765)
        deviceId = prefs.getString(KEY_DEVICE_ID, "") ?: ""
        deviceName = prefs.getString(KEY_DEVICE_NAME, "Android Device") ?: "Android Device"
        paired = prefs.getBoolean(KEY_PAIRED, false)
        
        if (deviceId.isEmpty()) {
            deviceId = "android_${java.util.UUID.randomUUID().toString().substring(0, 8)}"
            savePrefs()
        }
    }

    private fun savePrefs() {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit()
            .putString(KEY_SERVER_HOST, serverHost)
            .putInt(KEY_SERVER_PORT, serverPort)
            .putString(KEY_DEVICE_ID, deviceId)
            .putString(KEY_DEVICE_NAME, deviceName)
            .putBoolean(KEY_PAIRED, paired)
            .apply()
    }

    private fun initDeviceId() {
        if (deviceId.isEmpty()) {
            deviceId = "android_${java.util.UUID.randomUUID().toString().substring(0, 8)}"
            savePrefs()
        }
    }

    private fun initHttpClient() {
        client = HttpClient(CIO) {
            install(ContentNegotiation) {
                json()
            }
            install(Logging) {
                level = LogLevel.ALL
            }
        }
    }

    private fun registerReceivers() {
        // Accessibility ready receiver
        registerReceiver(accessibilityReceiver, IntentFilter(ACTION_ACCESSIBILITY_READY))
        
        // Notification listener ready receiver
        registerReceiver(notificationListenerReceiver, IntentFilter(ACTION_NOTIFICATION_LISTENER_READY))
        
        // New notification receiver
        registerReceiver(notificationReceiver, IntentFilter(ACTION_NEW_NOTIFICATION))
        
        // Send request receiver
        registerReceiver(requestReceiver, IntentFilter(ACTION_SEND_REQUEST))
    }

    private val accessibilityReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            Timber.d("Accessibility service ready")
            if (isConnected) {
                sendNotification(WsMessage(
                    action = "accessibility_ready",
                    params = mapOf("deviceId" to deviceId)
                ))
            }
        }
    }

    private val notificationListenerReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            Timber.d("Notification listener ready")
            if (isConnected) {
                sendNotification(WsMessage(
                    action = "notification_listener_ready",
                    params = mapOf("deviceId" to deviceId)
                ))
            }
        }
    }

    private val notificationReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val jsonStr = intent.getStringExtra("notification_json") ?: return
            try {
                val notification = json.decodeFromString<Notification>(jsonStr)
                if (isConnected) {
                    sendNotification(WsMessage(
                        action = "notification_posted",
                        params = mapOf("notification" to notification)
                    ))
                }
            } catch (e: Exception) {
                Timber.e(e, "Failed to parse notification")
            }
        }
    }

    private val requestReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val action = intent.getStringExtra("action") ?: return
            val id = intent.getIntExtra("id", 0)
            val paramsJson = intent.getStringExtra("params") ?: "{}"
            
            scope.launch {
                when (action) {
                    "tap" -> handleTap(id, paramsJson)
                    "swipe" -> handleSwipe(id, paramsJson)
                    "type_text" -> handleTypeText(id, paramsJson)
                    "open_app" -> handleOpenApp(id, paramsJson)
                    "get_notifications" -> handleGetNotifications(id)
                    "media_control" -> handleMediaControl(id, paramsJson)
                    "answer_call" -> handleAnswerCall(id)
                    "decline_call" -> handleDeclineCall(id)
                    "open_youtube" -> handleOpenYouTube(id, paramsJson)
                    "take_screenshot" -> handleScreenshot(id)
                    "get_device_info" -> handleDeviceInfo(id)
                    "get_screen_state" -> handleScreenState(id, paramsJson)
                }
            }
        }
    }

    // Handlers
    private suspend fun handleTap(id: Int, paramsJson: String) {
        val params = json.decodeFromString<TapParams>(paramsJson)
        val success = AccessibilityService.getInstance()?.performTap(params) ?: false
        sendResponse(id, success, if (success) null else "Accessibility service not available")
    }

    private suspend fun handleSwipe(id: Int, paramsJson: String) {
        val params = json.decodeFromString<SwipeParams>(paramsJson)
        val success = AccessibilityService.getInstance()?.performSwipe(params) ?: false
        sendResponse(id, success, if (success) null else "Accessibility service not available")
    }

    private suspend fun handleTypeText(id: Int, paramsJson: String) {
        val params = json.decodeFromString<TypeTextParams>(paramsJson)
        val success = AccessibilityService.getInstance()?.performTypeText(params.text) ?: false
        sendResponse(id, success, if (success) null else "Accessibility service not available")
    }

    private suspend fun handleOpenApp(id: Int, paramsJson: String) {
        val params = json.decodeFromString<OpenAppParams>(paramsJson)
        val success = try {
            val intent = packageManager.getLaunchIntentForPackage(params.packageName)
            if (intent != null) {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                startActivity(intent)
                true
            } else {
                false
            }
        } catch (e: Exception) {
            Timber.e(e, "Open app failed")
            false
        }
        sendResponse(id, success, if (success) null else "Package not found")
    }

    private suspend fun handleGetNotifications(id: Int) {
        val notifications = NotificationListenerService.getNotifications(this)
        sendResponse(id, true, null, mapOf("notifications" to notifications))
    }

    private suspend fun handleMediaControl(id: Int, paramsJson: String) {
        val params = json.decodeFromString<MediaControlParams>(paramsJson)
        val success = when (params.action) {
            "play" -> sendMediaButton(KeyEvent.KEYCODE_MEDIA_PLAY)
            "pause" -> sendMediaButton(KeyEvent.KEYCODE_MEDIA_PAUSE)
            "next" -> sendMediaButton(KeyEvent.KEYCODE_MEDIA_NEXT)
            "previous" -> sendMediaButton(KeyEvent.KEYCODE_MEDIA_PREVIOUS)
            "stop" -> sendMediaButton(KeyEvent.KEYCODE_MEDIA_STOP)
            else -> false
        }
        sendResponse(id, success, if (success) null else "Unknown action")
    }

    private suspend fun handleAnswerCall(id: Int) {
        val success = try {
            val telecomManager = getSystemService(Context.TELECOM_SERVICE) as android.telecom.TelecomManager
            telecomManager.acceptRingingCall()
            true
        } catch (e: Exception) {
            Timber.e(e, "Answer call failed")
            false
        }
        sendResponse(id, success, if (success) null else "Call answer failed")
    }

    private suspend fun handleDeclineCall(id: Int) {
        val success = try {
            val telecomManager = getSystemService(Context.TELECOM_SERVICE) as android.telecom.TelecomManager
            telecomManager.endCall()
            true
        } catch (e: Exception) {
            Timber.e(e, "Decline call failed")
            false
        }
        sendResponse(id, success, if (success) null else "Call decline failed")
    }

    private suspend fun handleOpenYouTube(id: Int, paramsJson: String) {
        val params = json.decodeFromString<OpenYouTubeParams>(paramsJson)
        val success = try {
            val intent = Intent(Intent.ACTION_VIEW).apply {
                if (params.query.isNotEmpty()) {
                    data = android.net.Uri.parse("https://www.youtube.com/results?search_query=${params.query}")
                } else {
                    data = android.net.Uri.parse("https://www.youtube.com")
                }
                setPackage("com.google.android.youtube")
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            startActivity(intent)
            true
        } catch (e: Exception) {
            Timber.e(e, "Open YouTube failed")
            false
        }
        sendResponse(id, success, if (success) null else "YouTube not installed")
    }

    private suspend fun handleScreenshot(id: Int) {
        val success = try {
            // Use MediaProjection for screenshot (requires permission)
            // For now, return placeholder
            sendResponse(id, false, null, mapOf("error" to "Screenshot requires MediaProjection permission"))
            return@handleScreenshot
        } catch (e: Exception) {
            Timber.e(e, "Screenshot failed")
            sendResponse(id, false, "Screenshot failed")
        }
    }

    private suspend fun handleDeviceInfo(id: Int) {
        val info = DeviceInfo(
            deviceId = deviceId,
            name = deviceName,
            model = Build.MODEL,
            manufacturer = Build.MANUFACTURER,
            androidVersion = Build.VERSION.RELEASE,
            sdkInt = Build.VERSION.SDK_INT,
            screenWidth = resources.displayMetrics.widthPixels,
            screenHeight = resources.displayMetrics.heightPixels,
            density = resources.displayMetrics.density
        )
        sendResponse(id, true, null, mapOf("info" to info))
    }

    private suspend fun handleScreenState(id: Int, paramsJson: String) {
        // Return current screen state (app in foreground, etc.)
        val activityManager = getSystemService(Context.ACTIVITY_SERVICE) as android.app.ActivityManager
        val tasks = activityManager.getRunningTasks(1)
        val topActivity = tasks.firstOrNull()?.topActivity
        
        sendResponse(id, true, null, mapOf(
            "topPackage" to topActivity?.packageName,
            "topClass" to topActivity?.className
        ))
    }

    private fun sendMediaButton(keyCode: Int): Boolean {
        try {
            val intent = Intent(Intent.ACTION_MEDIA_BUTTON).apply {
                putExtra(Intent.EXTRA_KEY_EVENT, android.view.KeyEvent(android.view.KeyEvent.ACTION_DOWN, keyCode))
            }
            sendOrderedBroadcast(intent, null)
            
            val intentUp = Intent(Intent.ACTION_MEDIA_BUTTON).apply {
                putExtra(Intent.EXTRA_KEY_EVENT, android.view.KeyEvent(android.view.KeyEvent.ACTION_UP, keyCode))
            }
            sendOrderedBroadcast(intentUp, null)
            true
        } catch (e: Exception) {
            Timber.e(e, "Media button failed")
            false
        }
    }

    private fun sendResponse(id: Int, success: Boolean, error: String? = null, result: Map<String, Any>? = null) {
        val response = WsMessage(
            action = "response",
            id = id,
            success = success,
            error = error,
            result = result
        )
        sendNotification(response)
    }

    // WebSocket connection
    private fun connect() {
        if (isConnected) return
        
        reconnectScope.launch {
            while (!isConnected && !reconnectJob.isCancelled) {
                try {
                    Timber.d("Connecting to ws://$serverHost:$serverPort/ws")
                    
                    val wsClient = HttpClient(CIO) {
                        install(ContentNegotiation) { json() }
                        install(Logging) { level = LogLevel.ALL }
                    }
                    
                    val session = wsClient.webSocket(
                        method = HttpMethod.Get,
                        host = serverHost,
                        port = serverPort,
                        path = "/ws",
                    ) { ws ->
                        webSocketSession = ws
                        isConnected = true
                        Timber.d("WebSocket connected")
                        
                        // Send device info on connect
                        val initMsg = WsMessage(
                            action = "device_connect",
                            params = mapOf(
                                "deviceId" to deviceId,
                                "name" to deviceName,
                                "capabilities" to listOf(
                                    "accessibility", "notifications", "media", "calls", "apps"
                                )
                            )
                        )
                        ws.send(json.encodeToString(initMsg))
                        
                        // Listen for messages
                        ws.incoming.consumeEach { frame ->
                            when (frame) {
                                is Frame.Text -> handleWsMessage(frame.readText())
                                is Frame.Binary -> {
                                    // Handle binary if needed
                                }
                                is Frame.Close -> {
                                    Timber.d("WebSocket closed: ${frame.reason}")
                                    isConnected = false
                                }
                            }
                        }
                    }
                    
                    // Wait for session to close
                    session.closeReason.await()
                    
                } catch (e: Exception) {
                    Timber.e(e, "WebSocket connection failed")
                    isConnected = false
                }
                
                if (!reconnectJob.isCancelled) {
                    Timber.d("Reconnecting in 5 seconds...")
                    delay(5000)
                }
            }
        }
    }

    private fun handleWsMessage(text: String) {
        try {
            val message = json.decodeFromString<WsMessage>(text)
            
            // Handle response to our request
            message.id?.let { id ->
                pendingRequests[id]?.complete(message)
                pendingRequests.remove(id)
                return
            }
            
            // Handle incoming requests
            when (message.action) {
                "tap" -> {
                    message.params?.let { params ->
                        val tapParams = json.decodeFromString<TapParams>(json.encodeToString(params))
                        val success = AccessibilityService.getInstance()?.performTap(tapParams) ?: false
                        sendResponse(message.id!!, success)
                    }
                }
                "swipe" -> {
                    message.params?.let { params ->
                        val swipeParams = json.decodeFromString<SwipeParams>(json.encodeToString(params))
                        val success = AccessibilityService.getInstance()?.performSwipe(swipeParams) ?: false
                        sendResponse(message.id!!, success)
                    }
                }
                "type_text" -> {
                    message.params?.let { params ->
                        val typeParams = json.decodeFromString<TypeTextParams>(json.encodeToString(params))
                        val success = AccessibilityService.getInstance()?.performTypeText(typeParams.text) ?: false
                        sendResponse(message.id!!, success)
                    }
                }
                "open_app" -> {
                    message.params?.let { params ->
                        val openParams = json.decodeFromString<OpenAppParams>(json.encodeToString(params))
                        val success = try {
                            val intent = packageManager.getLaunchIntentForPackage(openParams.packageName)
                            if (intent != null) {
                                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                startActivity(intent)
                                true
                            } else false
                        } catch (e: Exception) { false }
                        sendResponse(message.id!!, success)
                    }
                }
                "get_notifications" -> {
                    val notifications = NotificationListenerService.getNotifications(this)
                    sendResponse(message.id!!, true, null, mapOf("notifications" to notifications))
                }
                "media_control" -> {
                    message.params?.let { params ->
                        val action = params["action"] as? String ?: ""
                        val success = when (action) {
                            "play" -> sendMediaButton(KeyEvent.KEYCODE_MEDIA_PLAY)
                            "pause" -> sendMediaButton(KeyEvent.KEYCODE_MEDIA_PAUSE)
                            "next" -> sendMediaButton(KeyEvent.KEYCODE_MEDIA_NEXT)
                            "previous" -> sendMediaButton(KeyEvent.KEYCODE_MEDIA_PREVIOUS)
                            "stop" -> sendMediaButton(KeyEvent.KEYCODE_MEDIA_STOP)
                            else -> false
                        }
                        sendResponse(message.id!!, success)
                    }
                }
                "answer_call" -> {
                    val success = try {
                        val telecomManager = getSystemService(Context.TELECOM_SERVICE) as android.telecom.TelecomManager
                        telecomManager.acceptRingingCall()
                        true
                    } catch (e: Exception) { false }
                    sendResponse(message.id!!, success)
                }
                "decline_call" -> {
                    val success = try {
                        val telecomManager = getSystemService(Context.TELECOM_SERVICE) as android.telecom.TelecomManager
                        telecomManager.endCall()
                        true
                    } catch (e: Exception) { false }
                    sendResponse(message.id!!, success)
                }
                "open_youtube" -> {
                    message.params?.let { params ->
                        val query = params["query"] as? String ?: ""
                        val success = try {
                            val intent = Intent(Intent.ACTION_VIEW).apply {
                                if (query.isNotEmpty()) {
                                    data = android.net.Uri.parse("https://www.youtube.com/results?search_query=$query")
                                } else {
                                    data = android.net.Uri.parse("https://www.youtube.com")
                                }
                                setPackage("com.google.android.youtube")
                                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                            }
                            startActivity(intent)
                            true
                        } catch (e: Exception) { false }
                        sendResponse(message.id!!, success)
                    }
                }
                "take_screenshot" -> {
                    sendResponse(message.id!!, false, "Requires MediaProjection")
                }
                "get_device_info" -> {
                    val info = DeviceInfo(
                        deviceId = deviceId,
                        name = deviceName,
                        model = Build.MODEL,
                        manufacturer = Build.MANUFACTURER,
                        androidVersion = Build.VERSION.RELEASE,
                        sdkInt = Build.VERSION.SDK_INT,
                        screenWidth = resources.displayMetrics.widthPixels,
                        screenHeight = resources.displayMetrics.heightPixels,
                        density = resources.displayMetrics.density
                    )
                    sendResponse(message.id!!, true, null, mapOf("info" to info))
                }
                "get_screen_state" -> {
                    val activityManager = getSystemService(Context.ACTIVITY_SERVICE) as android.app.ActivityManager
                    val tasks = activityManager.getRunningTasks(1)
                    val topActivity = tasks.firstOrNull()?.topActivity
                    sendResponse(message.id!!, true, null, mapOf(
                        "topPackage" to topActivity?.packageName,
                        "topClass" to topActivity?.className
                    ))
                }
                "ping" -> {
                    sendNotification(WsMessage(action = "pong", id = message.id))
                }
            }
        } catch (e: Exception) {
            Timber.e(e, "WS message handling failed")
        }
    }

    private fun sendNotification(message: WsMessage) {
        webSocketSession?.send(json.encodeToString(message))
    }

    private fun sendResponse(id: Int, success: Boolean, error: String? = null, result: Map<String, Any>? = null) {
        val response = WsMessage(
            action = "response",
            id = id,
            success = success,
            error = error,
            result = result
        )
        sendNotification(response)
    }

    // Foreground service
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "START_SERVICE") {
            startForeground()
            connect()
        }
        return START_STICKY
    }

    private fun startForeground() {
        val notification = createNotification()
        startForeground(NOTIFICATION_ID, notification)
    }

    private fun createNotification(): Notification {
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("IndusDroid")
            .setContentText(if (isConnected) "Connected to Indus" else "Connecting...")
            .setSmallIcon(R.drawable.ic_notification)
            .setContentIntent(pendingIntent)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setOngoing(true)
            .build()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Indus Connection",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Indus PC connection status"
                setShowBadge(false)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        reconnectJob.cancel()
        scope.coroutineContext.cancelChildren()
        webSocketSession?.close()
        client?.close()
        unregisterReceiver(accessibilityReceiver)
        unregisterReceiver(notificationListenerReceiver)
        unregisterReceiver(notificationReceiver)
        unregisterReceiver(requestReceiver)
    }
}