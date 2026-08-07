package com.indus.droid.accessibility

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.content.Context
import android.content.Intent
import android.os.Build
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import com.indus.droid.WebSocketService
import com.indus.droid.model.TapParams
import com.indus.droid.model.SwipeParams
import com.indus.droid.model.TypeTextParams
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import timber.log.Timber

class AccessibilityService : AccessibilityService() {

    private var pendingTap: TapParams? = null
    private var pendingSwipe: SwipeParams? = null
    private var pendingTypeText: String? = null

    override fun onCreate() {
        super.onCreate()
        Timber.d("AccessibilityService created")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // Handle accessibility events if needed
    }

    override fun onInterrupt() {
        Timber.d("AccessibilityService interrupted")
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        Timber.d("AccessibilityService connected")
        
        info.apply {
            eventTypes = AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED or
                AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED or
                AccessibilityEvent.TYPE_VIEW_CLICKED or
                AccessibilityEvent.TYPE_VIEW_FOCUSED or
                AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED
            
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            flags = AccessibilityServiceInfo.DEFAULT or
                AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS or
                AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS or
                AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
            
            notificationTimeout = 100
            canRetrieveWindowContent = true
        }
        
        // Notify WebSocket service that accessibility is ready
        val intent = Intent(WebSocketService.ACTION_ACCESSIBILITY_READY)
        sendBroadcast(intent)
    }

    fun performTap(params: TapParams): Boolean {
        return try {
            val root = rootInActiveWindow ?: return false
            performClickAt(root, params.x, params.y)
        } catch (e: Exception) {
            Timber.e(e, "Tap failed")
            false
        }
    }

    private fun performClickAt(node: AccessibilityNodeInfo, x: Int, y: Int): Boolean {
        if (node.boundsInScreen.contains(x, y)) {
            if (node.isClickable || node.isFocusable || node.isEnabled) {
                return node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
            }
        }
        
        for (i in 0 until node.childCount) {
            val child = node.getChild(i)
            if (child != null) {
                if (performClickAt(child, x, y)) {
                    return true
                }
            }
        }
        return false
    }

    fun performSwipe(params: SwipeParams): Boolean {
        return try {
            val root = rootInActiveWindow ?: return false
            val path = android.graphics.Path().apply {
                moveTo(params.x1.toFloat(), params.y1.toFloat())
                lineTo(params.x2.toFloat(), params.y2.toFloat())
            }
            
            val gesture = android.accessibilityservice.GestureDescription.Builder()
                .addStroke(android.accessibilityservice.GestureDescription.StrokeDescription(
                    path, 0, params.duration.toLong()
                ))
                .build()
            
            dispatchGesture(gesture, object : AccessibilityService.GestureResultCallback() {
                override fun onCompleted(gestureDescription: android.accessibilityservice.GestureDescription) {
                    Timber.d("Swipe completed")
                }
                
                override fun onCancelled(gestureDescription: android.accessibilityservice.GestureDescription) {
                    Timber.d("Swipe cancelled")
                }
            }, null)
            
            true
        } catch (e: Exception) {
            Timber.e(e, "Swipe failed")
            false
        }
    }

    fun performTypeText(text: String): Boolean {
        return try {
            val root = rootInActiveWindow ?: return false
            val focusedNode = findFocusedEditable(root)
            
            focusedNode?.let { node ->
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                    val arguments = Bundle().apply {
                        putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text)
                    }
                    node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, arguments)
                } else {
                    // Fallback for older versions
                    val pasteData = android.content.ClipData.newPlainText("indus_text", text)
                    val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
                    clipboard.primaryClip = pasteData
                    node.performAction(AccessibilityNodeInfo.ACTION_FOCUS)
                    node.performAction(AccessibilityNodeInfo.ACTION_PASTE)
                }
                true
            } ?: false
        } catch (e: Exception) {
            Timber.e(e, "Type text failed")
            false
        }
    }

    private fun findFocusedEditable(node: AccessibilityNodeInfo): AccessibilityNodeInfo? {
        if (node.isEditable && node.isFocused) {
            return node
        }
        
        for (i in 0 until node.childCount) {
            val child = node.getChild(i)
            child?.let {
                val result = findFocusedEditable(it)
                if (result != null) return result
            }
        }
        return null
    }

    // Public API for WebSocket service
    companion object {
        private var instance: AccessibilityService? = null
        
        fun getInstance(): AccessibilityService? = instance
        
        private set
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