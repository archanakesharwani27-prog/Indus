package com.indus.droid.model

import kotlinx.serialization.Serializable

@Serializable
data class WsMessage(
    val action: String,
    val id: Int? = null,
    val params: Map<String, Any>? = null,
    val success: Boolean? = null,
    val error: String? = null,
    val result: Map<String, Any>? = null,
    val notifications: List<Notification>? = null,
    val info: Map<String, Any>? = null,
)

@Serializable
data class Notification(
    val packageName: String,
    val title: String?,
    val text: String?,
    val timestamp: Long,
    val id: Int,
)

@Serializable
data class DeviceInfo(
    val deviceId: String,
    val name: String,
    val model: String,
    val manufacturer: String,
    val androidVersion: String,
    val sdkInt: Int,
    val screenWidth: Int,
    val screenHeight: Int,
    val density: Float,
)

@Serializable
data class PairingRequest(
    val deviceId: String,
    val pin: String,
)

@Serializable
data class PairingResponse(
    val success: Boolean,
    val deviceId: String?,
    val error: String?,
)

@Serializable
data class TapParams(
    val x: Int,
    val y: Int,
)

@Serializable
data class SwipeParams(
    val x1: Int,
    val y1: Int,
    val x2: Int,
    val y2: Int,
    val duration: Int = 300,
)

@Serializable
data class TypeTextParams(
    val text: String,
)

@Serializable
data class OpenAppParams(
    val packageName: String,
)

@Serializable
data class MediaControlParams(
    val action: String,
)

@Serializable
data class OpenYouTubeParams(
    val query: String = "",
)

@Serializable
data class ScreenStateParams(
    val includeScreenshot: Boolean = false,
)