package com.indus.droid.pairing

import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.util.Base64
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.indus.droid.R
import com.indus.droid.accessibility.AccessibilityService
import com.indus.droid.notification.NotificationListenerService
import com.indus.droid.websocket.WebSocketService
import com.indus.droid.databinding.ActivityPairingBinding
import com.journeyapps.barcodescanner.BarcodeEncoder
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import timber.log.Timber

class PairingActivity : AppCompatActivity() {

    private lateinit var binding: ActivityPairingBinding
    private var currentPin = ""
    private val json = Json { ignoreUnknownKeys = true }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityPairingBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupUI()
        generateNewPin()
        startDiscoveryListener()
    }

    private fun setupUI() {
        binding.btnGeneratePin.setOnClickListener { generateNewPin() }
        binding.btnConfirmPairing.setOnClickListener { confirmPairing() }
        binding.btnOpenAccessibility.setOnClickListener { openAccessibilitySettings() }
        binding.btnOpenNotificationListener.setOnClickListener { openNotificationListenerSettings() }
        binding.btnStartService.setOnClickListener { startWebSocketService() }
    }

    private fun generateNewPin() {
        currentPin = String.format("%06d", (Math.random() * 900000 + 100000).toInt())
        binding.tvPin.text = currentPin
        binding.tvPinStatus.text = "Show this PIN on your PC or scan the QR code"
        
        // Generate QR code
        val qrData = json.encodeToString(mapOf(
            "type" to "indus_pair",
            "deviceId" to getDeviceId(),
            "name" to getDeviceName(),
            "ip" to getLocalIpAddress(),
            "port" to 8765,
            "pin" to currentPin
        ))
        
        try {
            val encoder = BarcodeEncoder()
            val bitmap = encoder.encodeBitmap(qrData, com.google.zxing.BarcodeFormat.QR_CODE, 400, 400)
            binding.ivQrCode.setImageBitmap(bitmap)
        } catch (e: Exception) {
            Timber.e(e, "QR generation failed")
        }
    }

    private fun confirmPairing() {
        val enteredPin = binding.etPinEntry.text.toString().trim()
        
        if (enteredPin.isEmpty()) {
            binding.etPinEntry.error = "Enter PIN from PC"
            return
        }
        
        if (enteredPin == currentPin) {
            // PIN matches - save pairing
            savePairing(enteredPin)
            binding.tvPinStatus.text = "✅ Paired! Starting connection..."
            binding.tvPinStatus.setTextColor(ContextCompat.getColor(this, R.color.green))
            
            // Start WebSocket service
            startWebSocketService()
            
            // Go back to main after delay
            android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                finish()
            }, 2000)
        } else {
            binding.etPinEntry.error = "PIN mismatch"
        }
    }

    private fun savePairing(pin: String) {
        val prefs = getSharedPreferences(WebSocketService.PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit()
            .putString(WebSocketService.KEY_DEVICE_ID, getDeviceId())
            .putString(WebSocketService.KEY_DEVICE_NAME, getDeviceName())
            .putBoolean(WebSocketService.KEY_PAIRED, true)
            .apply()
    }

    private fun openAccessibilitySettings() {
        val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
        startActivity(intent)
    }

    private fun openNotificationListenerSettings() {
        val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
        startActivity(intent)
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
        
        // Check permissions
        checkPermissions()
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

    private fun startDiscoveryListener() {
        // TODO: Listen for UDP discovery broadcasts from PC
        // For now, just show the device IP
        binding.tvDeviceIp.text = "Device IP: ${getLocalIpAddress()}:8765"
    }

    private fun getDeviceId(): String {
        val prefs = getSharedPreferences(WebSocketService.PREFS_NAME, Context.MODE_PRIVATE)
        var deviceId = prefs.getString(WebSocketService.KEY_DEVICE_ID, "") ?: ""
        if (deviceId.isEmpty()) {
            deviceId = "android_${java.util.UUID.randomUUID().toString().substring(0, 8)}"
            prefs.edit().putString(WebSocketService.KEY_DEVICE_ID, deviceId).apply()
        }
        return deviceId
    }

    private fun getDeviceName(): String {
        return Build.MODEL
    }

    private fun getLocalIpAddress(): String {
        try {
            val networkInterfaces = java.net.NetworkInterface.getNetworkInterfaces()
            while (networkInterfaces.hasMoreElements()) {
                val networkInterface = networkInterfaces.nextElement()
                val inetAddresses = networkInterface.inetAddresses
                while (inetAddresses.hasMoreElements()) {
                    val inetAddress = inetAddresses.nextElement()
                    if (!inetAddress.isLoopbackAddress && inetAddress is java.net.Inet4Address) {
                        return inetAddress.hostAddress
                    }
                }
            }
        } catch (e: Exception) {
            Timber.e(e, "Get IP failed")
        }
        return "Unknown"
    }

    override fun onResume() {
        super.onResume()
        checkPermissions()
    }
}