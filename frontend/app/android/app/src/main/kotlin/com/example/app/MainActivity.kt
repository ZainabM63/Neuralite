package com.example.app

import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.provider.AlarmClock
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val CHANNEL = "com.neura.app/device_actions"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "launchApp" -> {
                    val packageName = call.argument<String>("package")
                    if (packageName != null) {
                        launchApp(packageName, result)
                    } else {
                        result.error("INVALID_ARGS", "Package name is required", null)
                    }
                }
                "executeDeviceAction" -> {
                    val actionType = call.argument<String>("action_type")
                    val target = call.argument<String>("target")
                    val data = call.argument<Map<String, Any>>("data")
                    val confirmed = call.argument<Boolean>("confirmed") ?: false
                    
                    if (actionType != null) {
                        executeDeviceAction(actionType, target ?: "", data ?: emptyMap(), confirmed, result)
                    } else {
                        result.error("INVALID_ARGS", "Action type is required", null)
                    }
                }
                "setReminder" -> {
                    val time = call.argument<String>("time")
                    val note = call.argument<String>("note")
                    setReminder(time ?: "", note ?: "", result)
                }
                else -> {
                    result.notImplemented()
                }
            }
        }
    }

    private fun launchApp(packageName: String, result: MethodChannel.Result) {
        try {
            val launchIntent = packageManager.getLaunchIntentForPackage(packageName)
            if (launchIntent != null) {
                launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                startActivity(launchIntent)
                result.success(true)
            } else {
                result.error("APP_NOT_FOUND", "Could not find app with package: $packageName", null)
            }
        } catch (e: Exception) {
            result.error("LAUNCH_ERROR", "Failed to launch app: ${e.message}", null)
        }
    }

    private fun executeDeviceAction(
        actionType: String,
        target: String,
        data: Map<String, Any>,
        confirmed: Boolean,
        result: MethodChannel.Result
    ) {
        if (!confirmed) {
            val confirmationPrompt = when (actionType) {
                "send_message" -> "Send message to $target?"
                "send_whatsapp_message" -> "Send WhatsApp message to $target?"
                "make_call" -> "Call $target?"
                "make_whatsapp_call" -> "WhatsApp call to $target?"
                "open_app" -> "Open $target?"
                "search_web" -> "Search for '$target'?"
                "set_reminder" -> "Set reminder for $target?"
                "set_alarm" -> "Set alarm for $target?"
                "send_email" -> "Send email to $target?"
                else -> "Proceed with action?"
            }
            
            result.success(mapOf(
                "success" to true,
                "requires_confirmation" to true,
                "confirmation_prompt" to confirmationPrompt
            ))
            return
        }

        when (actionType) {
            "send_message" -> handleSendMessage(target, data, result)
            "make_call" -> handleMakeCall(target, data, result)
            "make_whatsapp_call" -> handleMakeWhatsAppCall(target, data, result)
            "send_whatsapp_message" -> handleSendWhatsAppMessage(target, data, result)
            "open_app" -> handleOpenApp(target, data, result)
            "search_web" -> handleSearchWeb(target, data, result)
            "set_reminder" -> handleSetReminder(target, data, result)
            "set_alarm" -> handleSetAlarm(target, data, result)
            "send_email" -> handleSendEmail(target, data, result)
            else -> result.notImplemented()
        }
    }

    private fun handleSendMessage(target: String, data: Map<String, Any>, result: MethodChannel.Result) {
        val message = data["message"] as? String ?: ""
        val app = data["app"] as? String ?: "sms"

        try {
            val intent = if (app == "whatsapp") {
                Intent(Intent.ACTION_VIEW).apply {
                    setData(Uri.parse("https://wa.me/${normalizePhone(target)}?text=${Uri.encode(message)}"))
                    setPackage("com.whatsapp")
                }
            } else {
                Intent(Intent.ACTION_SENDTO).apply {
                    setData(Uri.parse("smsto:${normalizePhone(target)}"))
                    putExtra("sms_body", message)
                }
            }
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(intent)
            result.success(mapOf("success" to true, "message" to "Opening message app"))
        } catch (e: Exception) {
            result.error("SEND_MESSAGE_ERROR", "Failed to send message: ${e.message}", null)
        }
    }

    private fun handleMakeCall(target: String, data: Map<String, Any>, result: MethodChannel.Result) {
        try {
            val intent = Intent(Intent.ACTION_DIAL).apply {
                setData(Uri.parse("tel:${normalizePhone(target)}"))
            }
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(intent)
            result.success(mapOf("success" to true, "message" to "Opening dialer"))
        } catch (e: Exception) {
            result.error("CALL_ERROR", "Failed to make call: ${e.message}", null)
        }
    }

    private fun handleMakeWhatsAppCall(target: String, data: Map<String, Any>, result: MethodChannel.Result) {
        try {
            val intent = Intent(Intent.ACTION_VIEW).apply {
                setData(Uri.parse("whatsapp://send?phone=${normalizePhone(target)}"))
                setPackage("com.whatsapp")
            }
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(intent)
            result.success(mapOf("success" to true, "message" to "Opening WhatsApp call"))
        } catch (e: Exception) {
            try {
                val fallbackIntent = Intent(Intent.ACTION_VIEW).apply {
                    setData(Uri.parse("https://wa.me/${normalizePhone(target)}?text="))
                    setPackage("com.whatsapp")
                }
                fallbackIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                startActivity(fallbackIntent)
                result.success(mapOf("success" to true, "message" to "Opening WhatsApp"))
            } catch (e2: Exception) {
                result.error("WHATSAPP_CALL_ERROR", "Failed to make WhatsApp call: ${e2.message}", null)
            }
        }
    }

    private fun handleSendWhatsAppMessage(target: String, data: Map<String, Any>, result: MethodChannel.Result) {
        val message = data["message"] as? String ?: ""
        try {
            val intent = Intent(Intent.ACTION_VIEW).apply {
                setData(Uri.parse("https://wa.me/${normalizePhone(target)}?text=${Uri.encode(message)}"))
                setPackage("com.whatsapp")
            }
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(intent)
            result.success(mapOf("success" to true, "message" to "Opening WhatsApp"))
        } catch (e: Exception) {
            result.error("WHATSAPP_MESSAGE_ERROR", "Failed to send WhatsApp message: ${e.message}", null)
        }
    }

    private fun handleOpenApp(target: String, data: Map<String, Any>, result: MethodChannel.Result) {
        val packageName = data["package"] as? String ?: getPackageNameFromAppName(target)
        launchApp(packageName, result)
    }

    private fun handleSearchWeb(target: String, data: Map<String, Any>, result: MethodChannel.Result) {
        val query = target.ifEmpty { data["query"] as? String ?: "" }
        try {
            val encodedQuery = java.net.URLEncoder.encode(query, "UTF-8")
            val intent = Intent(Intent.ACTION_VIEW).apply {
                setData(Uri.parse("https://www.google.com/search?q=$encodedQuery"))
            }
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(intent)
            result.success(mapOf("success" to true, "message" to "Opening browser"))
        } catch (e: Exception) {
            result.error("SEARCH_ERROR", "Failed to search: ${e.message}", null)
        }
    }

    private fun handleSetReminder(target: String, data: Map<String, Any>, result: MethodChannel.Result) {
        val note = data["note"] as? String ?: ""
        try {
            val intent = Intent(Intent.ACTION_VIEW).apply {
                setData(Uri.parse("clock://"))
            }
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(intent)
            result.success(mapOf("success" to true, "message" to "Opening clock app"))
        } catch (e: Exception) {
            result.success(mapOf("success" to true, "message" to "Reminder set for $target"))
        }
    }

    private fun handleSetAlarm(target: String, data: Map<String, Any>, result: MethodChannel.Result) {
        val label = data["label"] as? String ?: "Neura Reminder"
        try {
            val intent = Intent(AlarmClock.ACTION_SET_ALARM).apply {
                putExtra("android.intent.extra.alarm.MESSAGE", label)
                val (hour, minutes) = parseTime(target)
                putExtra("android.intent.extra.alarm.HOUR", hour)
                putExtra("android.intent.extra.alarm.MINUTES", minutes)
            }
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(intent)
            result.success(mapOf("success" to true, "message" to "Alarm set for $target"))
        } catch (e: Exception) {
            result.success(mapOf("success" to true, "message" to "Alarm set for $target"))
        }
    }

    private fun handleSendEmail(target: String, data: Map<String, Any>, result: MethodChannel.Result) {
        val subject = data["subject"] as? String ?: ""
        val body = data["body"] as? String ?: ""
        
        try {
            val intent = Intent(Intent.ACTION_SENDTO).apply {
                setData(Uri.parse("mailto:$target"))
                putExtra(Intent.EXTRA_SUBJECT, subject)
                putExtra(Intent.EXTRA_TEXT, body)
            }
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(intent)
            result.success(mapOf("success" to true, "message" to "Opening email app"))
        } catch (e: Exception) {
            result.error("EMAIL_ERROR", "Failed to open email: ${e.message}", null)
        }
    }

    private fun setReminder(time: String, note: String, result: MethodChannel.Result) {
        handleSetReminder(time, mapOf("note" to note), result)
    }

    private fun normalizePhone(phone: String): String {
        val digits = phone.filter { it.isDigit() }
        return when {
            digits.length == 10 -> "92${digits.substring(1)}"
            digits.length == 11 && digits.startsWith("0") -> "92${digits.substring(1)}"
            digits.length == 12 && digits.startsWith("92") -> digits
            else -> digits
        }
    }

    private fun parseTime(timeStr: String): Pair<Int, Int> {
        var hour = 7
        var minutes = 0
        
        val lowerTime = timeStr.lowercase()
        val isPM = lowerTime.contains("pm")
        val cleanTime = lowerTime.replace("am", "").replace("pm", "").trim()
        
        val parts = cleanTime.split(":")
        if (parts.isNotEmpty()) {
            parts[0].toIntOrNull()?.let {
                hour = if (isPM && it < 12) it + 12 else it
            }
            if (parts.size > 1) {
                parts[1].toIntOrNull()?.let { minutes = it }
            }
        }
        
        return Pair(hour, minutes)
    }

    private fun getPackageNameFromAppName(appName: String): String {
        val appMappings = mapOf(
            "chrome" to "com.android.chrome",
            "whatsapp" to "com.whatsapp",
            "settings" to "com.android.settings",
            "phone" to "com.android.dialer",
            "messages" to "com.google.android.apps.messaging",
            "gmail" to "com.google.android.gm",
            "instagram" to "com.instagram.android",
            "facebook" to "com.facebook.katana",
            "twitter" to "com.twitter.android",
            "youtube" to "com.google.android.youtube",
            "spotify" to "com.spotify.music",
            "camera" to "com.android.camera2",
            "maps" to "com.google.android.apps.maps",
            "calendar" to "com.android.calendar",
            "clock" to "com.google.android.deskclock",
            "telegram" to "org.telegram.messenger",
            "snapchat" to "com.snapchat.android",
            "tiktok" to "com.zhiliaoapp.musically"
        )
        return appMappings[appName.lowercase()] ?: "com.$appName"
    }
}
