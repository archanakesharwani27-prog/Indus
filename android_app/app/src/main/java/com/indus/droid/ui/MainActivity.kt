package com.indus.droid.ui

import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.Menu
import android.view.MenuItem
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.indus.droid.R
import com.indus.droid.accessibility.AccessibilityService
import com.indus.droid.notification.NotificationListenerService
import com.indus.droid.pairing.PairingActivity
import com.indus.droid.websocket.WebSocketService
import com.indus.droid.databinding.ActivityMainBinding
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import timber.log.Timber

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val permissionLauncher = registerForActivityResult(
        android.content.pm.PackageManager.RequestPermissionResultContract()
    ) { granted ->
        checkPermissions()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setSupportActionBar(binding.toolbar)
        setupUI()
        checkPermissions()
        checkPairingStatus()
    }

    private fun setupUI() {
        binding.btnPairNew.setOnClickListener {
            startActivity(Intent(this, PairingActivity::class.java))
        }
        
        binding.btnStartService.setOnClickListener {
            startWebSocketService()
        }
        
        binding.btnStopService.setOnClickListener {
            stopWebSocketService()
        }
        
        binding.btnOpenAccessibility.setOnClickListener {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }
        
        binding.btnOpenNotificationListener.setOnClickListener {
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        }
        
        binding.btnTestConnection.setOnClickListener {
            testConnection()
        }
    }

    private fun checkPermissions() {
        // Check accessibility
        val accessibilityEnabled = isAccessibilityServiceEnabled()
        binding.tvAccessibilityStatus.text = if (accessibilityEnabled) "✅ Enabled" else "❌ Not enabled"
        binding.tvAccessibilityStatus.setTextColor(ContextCompat.getColor(
            this, if (accessibilityEnabled) R.color.green else R.color.red
        ))
        
        // Check notification listener
        val notificationEnabled = isNotificationListenerEnabled()
        binding.tvNotificationStatus.text = if (notificationEnabled) "✅ Enabled" else "❌ Not enabled"
        binding.tvNotificationStatus.setTextColor(ContextCompat.getColor(
            this, if (notificationEnabled) R.color.green else R.color.red
        ))
        
        // Check if paired
        val prefs = getSharedPreferences(WebSocketService.PREFS_NAME, Context.MODE_PRIVATE)
        val paired = prefs.getBoolean(WebSocketService.KEY_PAIRED, false)
        binding.tvPairStatus.text = if (paired) "✅ Paired" else "❌ Not paired"
        binding.tvPairStatus.setTextColor(ContextCompat.getColor(
            this, if (paired) R.color.green else R.color.red
        ))
        
        binding.btnPairNew.isEnabled = !paired
        binding.btnStartService.isEnabled = paired
    }

    private fun checkPairingStatus() {
        val prefs = getSharedPreferences(WebSocketService.PREFS_NAME, Context.MODE_PRIVATE)
        val paired = prefs.getBoolean(WebSocketService.KEY_PAIRED, false)
        
        if (paired) {
            val deviceId = prefs.getString(WebSocketService.KEY_DEVICE_ID, "")
            val deviceName = prefs.getString(WebSocketService.KEY_DEVICE_NAME, "")
            val serverHost = prefs.getString(WebSocketService.KEY_SERVER_HOST, "")
            val serverPort = prefs.getInt(WebSocketService.KEY_SERVER_PORT, 8765)
            
            binding.tvDeviceInfo.text = "Device: $deviceName ($deviceId)\nServer: $serverHost:$serverPort"
        } else {
            binding.tvDeviceInfo.text = "Not paired with any PC"
        }
    }

    private fun isAccessibilityServiceEnabled(): Boolean {
        val accessibilityManager = getSystemService(Context.ACCESSIBILITY_SERVICE) as android.view.accessibility.AccessibilityManager
        val services = accessibilityManager.getEnabledAccessibilityServiceList(android.accessibilityservice.AccessibilityServiceInfo.FEEDBACK_GENERIC)
        return services.any { it.id.contains("AccessibilityService") }
    }

    private fun isNotificationListenerEnabled(): Boolean {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as android.app.NotificationManager
        val enabledListeners = notificationManager.enabledNotificationListeners
        return enabledListeners?.any { it.flattenToString().contains("NotificationListenerService") } ?: false
    }

    private fun startWebSocketService() {
        val intent = Intent(this, WebSocketService::class.java).apply {
            action = "START_SERVICE"
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
        
        binding.tvServiceStatus.text = "Service: Starting..."
        binding.tvServiceStatus.setTextColor(ContextCompat.getColor(this, R.color.orange))
        
        // Update UI after delay
        android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
            checkServiceStatus()
        }, 3000)
    }

    private fun stopWebSocketService() {
        val intent = Intent(this, WebSocketService::class.java)
        stopService(intent)
        binding.tvServiceStatus.text = "Service: Stopped"
        binding.tvServiceStatus.setTextColor(ContextCompat.getColor(this, R.color.red))
    }

    private fun checkServiceStatus() {
        // Check if service is running
        val manager = getSystemService(Context.ACTIVITY_SERVICE) as android.app.ActivityManager
        val services = manager.getRunningServices(Integer.MAX_VALUE)
        val isRunning = services.any { it.service.className == WebSocketService::class.java.name }
        
        binding.tvServiceStatus.text = if (isRunning) "Service: Running" else "Service: Stopped"
        binding.tvServiceStatus.setTextColor(ContextCompat.getColor(
            this, if (isRunning) R.color.green else R.color.red
        ))
    }

    private fun testConnection() {
        // Send test message via broadcast to WebSocket service
        val intent = Intent(WebSocketService.ACTION_SEND_REQUEST).apply {
            putExtra("action", "get_device_info")
            putExtra("id", 999)
            putExtra("params", "{}")
        }
        sendBroadcast(intent)
        
        binding.tvTestResult.text = "Test request sent. Check PC for response."
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.main_menu, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_settings -> {
                // Open settings
                true
            }
            R.id.action_unpair -> {
                unpairDevice()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    private fun unpairDevice() {
        val prefs = getSharedPreferences(WebSocketService.PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().clear().apply()
        stopWebSocketService()
        checkPermissions()
        checkPairingStatus()
        binding.tvDeviceInfo.text = "Not paired with any PC"
    }
}