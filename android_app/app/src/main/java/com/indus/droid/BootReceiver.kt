package com.indus.droid

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.os.Build
import timber.log.Timber

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED 
            || intent.action == Intent.ACTION_QUICKBOOT_POWERON) {
            
            Timber.d("Boot completed, checking auto-start")
            
            val prefs = context.getSharedPreferences(WebSocketService.PREFS_NAME, Context.MODE_PRIVATE)
            val autoStart = prefs.getBoolean(WebSocketService.KEY_AUTO_START, true)
            val paired = prefs.getBoolean(WebSocketService.KEY_PAIRED, false)
            
            if (autoStart && paired) {
                val serviceIntent = Intent(context, WebSocketService::class.java).apply {
                    action = "START_SERVICE"
                }
                
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(serviceIntent)
                } else {
                    context.startService(serviceIntent)
                }
                
                Timber.d("WebSocketService started on boot")
            }
        }
    }
}