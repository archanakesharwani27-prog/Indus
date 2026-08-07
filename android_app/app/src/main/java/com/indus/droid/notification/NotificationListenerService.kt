package com.indus.droid.notification

import android.content.Context
import android.content.Intent
import android.os.Build
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import com.indus.droid.WebSocketService
import com.indus.droid.model.Notification
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import timber.log.Timber

class NotificationListenerService : NotificationListenerService() {

    private val json = Json { ignoreUnknownKeys = true }

    override fun onCreate() {
        super.onCreate()
        Timber.d("NotificationListenerService created")
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        super.onNotificationPosted(sbn)
        
        val pkg = sbn.packageName
        val notification = sbn.notification
        
        // Extract title and text
        var title: String? = null
        var text: String? = null
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT_WATCH) {
            val extras = notification.extras
            title = extras.getCharSequence(android.app.Notification.EXTRA_TITLE)?.toString()
            text = extras.getCharSequence(android.app.Notification.EXTRA_TEXT)?.toString()
            
            // Also try big text
            if (text.isNullOrEmpty()) {
                text = extras.getCharSequence(android.app.Notification.EXTRA_BIG_TEXT)?.toString()
            }
            
            // Try messaging style
            if (text.isNullOrEmpty()) {
                val messages = extras.getParcelableArray(android.app.Notification.EXTRA_MESSAGES)
                messages?.forEach { msg ->
                    if (msg is android.app.Notification.MessagingStyle.Message) {
                        text = msg.text?.toString()
                    }
                }
            }
        }
        
        val notif = Notification(
            packageName = pkg,
            title = title,
            text = text,
            timestamp = sbn.postTime,
            id = sbn.id
        )
        
        Timber.d("Notification from $pkg: $title - $text")
        
        // Send to WebSocket service
        sendNotificationToService(notif)
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {
        super.onNotificationRemoved(sbn)
        Timber.d("Notification removed: ${sbn.packageName} id=${sbn.id}")
    }

    override fun onListenerConnected() {
        super.onListenerConnected()
        Timber.d("NotificationListenerService connected")
        
        // Notify WebSocket service
        val intent = Intent(WebSocketService.ACTION_NOTIFICATION_LISTENER_READY)
        sendBroadcast(intent)
    }

    private fun sendNotificationToService(notification: Notification) {
        CoroutineScope(Dispatchers.IO).launch {
            val jsonStr = json.encodeToString(notification)
            val intent = Intent(WebSocketService.ACTION_NEW_NOTIFICATION)
                .putExtra("notification_json", jsonStr)
            sendBroadcast(intent)
        }
    }

    // Public API
    companion object {
        private var instance: NotificationListenerService? = null
        
        fun getInstance(): NotificationListenerService? = instance
        
        fun getNotifications(context: Context): List<Notification> {
            return instance?.getActiveNotifications(context) ?: emptyList()
        }
        
        private fun getActiveNotifications(context: Context): List<Notification> {
            val sbns = getActiveNotifications()
            return sbns.map { sbn ->
                val notification = sbn.notification
                var title: String? = null
                var text: String? = null
                
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT_WATCH) {
                    val extras = notification.extras
                    title = extras.getCharSequence(android.app.Notification.EXTRA_TITLE)?.toString()
                    text = extras.getCharSequence(android.app.Notification.EXTRA_TEXT)?.toString()
                    if (text.isNullOrEmpty()) {
                        text = extras.getCharSequence(android.app.Notification.EXTRA_BIG_TEXT)?.toString()
                    }
                }
                
                Notification(
                    packageName = sbn.packageName,
                    title = title,
                    text = text,
                    timestamp = sbn.postTime,
                    id = sbn.id
                )
            }.toList()
        }
    }
    
    override fun onCreate() {
        super.onCreate()
        instance = this
    }
    
    override fun onDestroy() {
        instance = null
        super.onDestroy()
    }
}