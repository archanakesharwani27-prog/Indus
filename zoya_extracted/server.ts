import { GoogleGenAI, LiveServerMessage, Modality, Type } from "@google/genai";
import express from "express";
import http from "http";
import path from "path";
import { WebSocketServer, WebSocket } from "ws";
import { createServer as createViteServer } from "vite";
import {
  loadMemories,
  addOrUpdateMemory,
  deleteMemory,
  clearAllMemories,
  buildSystemMemoryPrompt,
} from "./server/memoryStore";
import {
  loadHabits,
  logHabitCompletion,
  addHabit,
  deleteHabit,
  buildHabitSystemPrompt,
} from "./server/habitStore";
import {
  registerOrHeartbeatDevice,
  loadDevices,
  createRemoteCommand,
  getPendingCommandsForDevice,
  markCommandExecuted,
} from "./server/deviceStore";

const PORT = 3000;

const sendCrossDeviceCommandDeclaration = {
  name: "sendCrossDeviceCommand",
  description: "Sends a remote command to execute an action on the user's other connected device (e.g., from PC to Mobile, or Mobile to PC). Useful when the user asks Zoya to perform an action on their mobile phone from PC or vice versa!",
  parameters: {
    type: Type.OBJECT,
    properties: {
      targetDevice: {
        type: Type.STRING,
        description: "Target device type: 'mobile', 'desktop', or 'all'.",
      },
      action: {
        type: Type.STRING,
        description: "Action to execute: 'openWebsite', 'changeAuraTheme', 'triggerAlert', 'speakMessage'.",
      },
      targetUrl: {
        type: Type.STRING,
        description: "URL or website to open on the remote device if action is 'openWebsite'.",
      },
      alertMessage: {
        type: Type.STRING,
        description: "Message or alert text to display on the remote device.",
      },
    },
    required: ["targetDevice", "action"],
  },
};

const listConnectedDevicesDeclaration = {
  name: "listConnectedDevices",
  description: "Lists all currently active connected devices logged in under the user's account.",
  parameters: {
    type: Type.OBJECT,
    properties: {},
  },
};

const saveMemoryDeclaration = {
  name: "saveMemory",
  description: "Saves a permanent memory or key detail about the user into Zoya's long-term memory vault (e.g., user name, favorite food, location, hobbies, past chat topic, secrets, promises). Always call this when the user shares personal details or asks you to remember something!",
  parameters: {
    type: Type.OBJECT,
    properties: {
      key: {
        type: Type.STRING,
        description: "The memory title or topic key (e.g. 'User Name', 'Favorite Food', 'Hobby', 'Past Chat Detail').",
      },
      value: {
        type: Type.STRING,
        description: "The detail to remember (e.g. 'Rahul', 'Paneer Tikka', 'Loves playing cricket').",
      },
      category: {
        type: Type.STRING,
        description: "Category: 'profile', 'preference', 'conversation', 'fact', 'secret'.",
      },
    },
    required: ["key", "value"],
  },
};

const forgetMemoryDeclaration = {
  name: "forgetMemory",
  description: "Deletes or removes a specific memory from Zoya's memory vault when requested by the user.",
  parameters: {
    type: Type.OBJECT,
    properties: {
      key: {
        type: Type.STRING,
        description: "The key or topic of the memory to remove.",
      },
    },
    required: ["key"],
  },
};

const openWebsiteDeclaration = {
  name: "openWebsite",
  description: "Opens a website or URL in the user's browser (e.g., Google, YouTube, GitHub, Wikipedia, Spotify, etc.).",
  parameters: {
    type: Type.OBJECT,
    properties: {
      url: {
        type: Type.STRING,
        description: "The complete web address or URL to open (e.g. 'https://youtube.com', 'https://google.com', 'https://wikipedia.org').",
      },
      targetName: {
        type: Type.STRING,
        description: "Name of the website or platform being opened.",
      },
    },
    required: ["url"],
  },
};

const changeAuraThemeDeclaration = {
  name: "changeAuraTheme",
  description: "Changes Zoya's visual background aura theme or mood.",
  parameters: {
    type: Type.OBJECT,
    properties: {
      theme: {
        type: Type.STRING,
        description: "Theme choice: 'neon-cyber', 'sassy-pink', 'electric-violet', 'cosmic-emerald', 'midnight-gold'.",
      },
    },
    required: ["theme"],
  },
};

const triggerQuickActionDeclaration = {
  name: "triggerQuickAction",
  description: "Triggers a quick playful visual or sound effect action on Zoya's interface.",
  parameters: {
    type: Type.OBJECT,
    properties: {
      action: {
        type: Type.STRING,
        description: "Action type: 'wink', 'flirt-sparkle', 'confidence-boost', 'tell-secret'.",
      },
    },
    required: ["action"],
  },
};

const logHabitDeclaration = {
  name: "logHabit",
  description: "Logs completion of a daily habit (e.g. 'drink water', 'exercise', 'workout', 'read 10 pages', 'meditate'). Automatically updates daily count, streak, and generates Zoya's encouraging response!",
  parameters: {
    type: Type.OBJECT,
    properties: {
      habitName: {
        type: Type.STRING,
        description: "Name or type of habit (e.g. 'drink water', 'exercise', 'read', 'meditate').",
      },
      notes: {
        type: Type.STRING,
        description: "Optional notes or quantity detail (e.g. '2 glasses of water', '30 mins workout').",
      },
    },
    required: ["habitName"],
  },
};

const getHabitStatusDeclaration = {
  name: "getHabitStatus",
  description: "Retrieves the user's daily habit tracking status, current streaks, and today's progress.",
  parameters: {
    type: Type.OBJECT,
    properties: {},
  },
};

const announceIncomingCallDeclaration = {
  name: "announceIncomingCall",
  description: "Announces an incoming phone call and reads out loud the caller's name and relationship to the user.",
  parameters: {
    type: Type.OBJECT,
    properties: {
      callerName: {
        type: Type.STRING,
        description: "Name of the caller (e.g. 'Papa', 'Mom', 'Rohit', 'Boss', 'Unknown Number').",
      },
      relationship: {
        type: Type.STRING,
        description: "Relationship or tag (e.g. 'Father', 'Mother', 'Best Friend', 'Work Boss').",
      },
      phoneNumber: {
        type: Type.STRING,
        description: "Optional phone number string.",
      },
    },
    required: ["callerName"],
  },
};

const handleCallActionDeclaration = {
  name: "handleCallAction",
  description: "Handles user command to accept (pick up) or decline (reject/disconnect) an active incoming call.",
  parameters: {
    type: Type.OBJECT,
    properties: {
      action: {
        type: Type.STRING,
        description: "Call action: 'accept' (pick up call), 'decline' (reject call), 'mute' (silence ringing), or 'quick_reply'.",
      },
      replyMessage: {
        type: Type.STRING,
        description: "Optional SMS reply message when declining (e.g. 'I am busy right now, calling back later').",
      },
    },
    required: ["action"],
  },
};

const controlPcAppDeclaration = {
  name: "controlPcApp",
  description: "Launches or opens a desktop PC application or tool (e.g. 'Calculator', 'Notepad', 'VS Code', 'Task Manager', 'Terminal', 'Chrome', 'Spotify', 'YouTube', 'Paint', 'File Explorer').",
  parameters: {
    type: Type.OBJECT,
    properties: {
      appName: {
        type: Type.STRING,
        description: "Name of the app to launch (e.g. 'Calculator', 'Notepad', 'VS Code', 'Task Manager', 'Terminal', 'Chrome', 'Spotify', 'YouTube').",
      },
      url: {
        type: Type.STRING,
        description: "Optional URL if opening a web app or site.",
      },
    },
    required: ["appName"],
  },
};

const controlPcAudioDeclaration = {
  name: "controlPcAudio",
  description: "Controls PC speaker volume or audio playback (e.g., mute, unmute, set volume to X%, play/pause media, skip track).",
  parameters: {
    type: Type.OBJECT,
    properties: {
      action: {
        type: Type.STRING,
        description: "Action type: 'set_volume', 'mute', 'unmute', 'play_pause', 'next', 'prev'.",
      },
      volumeLevel: {
        type: Type.NUMBER,
        description: "Volume percentage from 0 to 100 if action is 'set_volume'.",
      },
    },
    required: ["action"],
  },
};

const controlPcSystemDeclaration = {
  name: "controlPcSystem",
  description: "Executes system-level actions on the PC (e.g., take screenshot, lock screen, sleep mode, clear temporary cache, flush DNS, check CPU/RAM system status).",
  parameters: {
    type: Type.OBJECT,
    properties: {
      action: {
        type: Type.STRING,
        description: "System action: 'screenshot', 'lock_screen', 'sleep', 'clean_temp', 'system_status', 'flush_dns'.",
      },
    },
    required: ["action"],
  },
};

const runTerminalCommandDeclaration = {
  name: "runTerminalCommand",
  description: "Executes a safe terminal or command prompt command on the PC (e.g., 'ipconfig', 'ping google.com', 'dir', 'whoami', 'systeminfo', 'tasklist').",
  parameters: {
    type: Type.OBJECT,
    properties: {
      command: {
        type: Type.STRING,
        description: "The terminal or shell command to execute.",
      },
    },
    required: ["command"],
  },
};

const playMusicOrVideoDeclaration = {
  name: "playMusicOrVideo",
  description: "Immediately plays a song, music track, bhajan, or YouTube video in Zoya's embedded player (e.g., 'Hanuman Chalisa', 'Lut Le Gya song', 'Arijit Singh songs', 'Lofi beats', 'YouTube video').",
  parameters: {
    type: Type.OBJECT,
    properties: {
      query: {
        type: Type.STRING,
        description: "Song title, track name, bhajan, or search query (e.g. 'Hanuman Chalisa Gulshan Kumar', 'Lut Le Gya song').",
      },
      youtubeUrl: {
        type: Type.STRING,
        description: "Optional direct YouTube video or playlist URL if known.",
      },
      category: {
        type: Type.STRING,
        description: "Optional category (e.g., 'music', 'bhajan', 'lofi', 'video').",
      },
    },
    required: ["query"],
  },
};


async function startServer() {
  const app = express();
  app.use(express.json());

  const server = http.createServer(app);
  const wss = new WebSocketServer({ server, path: "/ws/live" });

  // API Health Endpoint
  app.get("/api/health", (_req, res) => {
    res.json({ status: "ok", name: "Zoya AI Assistant", version: "1.0.0" });
  });

  // REST API Endpoints for Memory System
  app.get("/api/memories", (_req, res) => {
    const memories = loadMemories();
    res.json({ success: true, memories });
  });

  app.post("/api/memories", (req, res) => {
    const { key, value, category } = req.body;
    if (!key || !value) {
      return res.status(400).json({ error: "key and value are required" });
    }
    const memory = addOrUpdateMemory(key, value, category || "fact");
    res.json({ success: true, memory });
  });

  app.delete("/api/memories/:id", (req, res) => {
    const { id } = req.params;
    const deleted = deleteMemory(id);
    res.json({ success: deleted });
  });

  app.delete("/api/memories", (_req, res) => {
    clearAllMemories();
    res.json({ success: true });
  });

  // REST API Endpoints for Daily Habit Tracker
  app.get("/api/habits", (_req, res) => {
    const habits = loadHabits();
    res.json({ success: true, habits });
  });

  app.post("/api/habits/log", (req, res) => {
    const { habitName, notes } = req.body;
    if (!habitName) {
      return res.status(400).json({ error: "habitName is required" });
    }
    const result = logHabitCompletion(habitName, notes);
    res.json({ success: true, habit: result.habit, remark: result.remark });
  });

  app.post("/api/habits", (req, res) => {
    const { name, category, targetCountDaily, icon } = req.body;
    if (!name) {
      return res.status(400).json({ error: "name is required" });
    }
    const habit = addHabit(name, category || "health", targetCountDaily || 1, icon || "Target");
    res.json({ success: true, habit });
  });

  app.delete("/api/habits/:id", (req, res) => {
    const { id } = req.params;
    const deleted = deleteHabit(id);
    res.json({ success: deleted });
  });

  // REST API Endpoints for Multi-Device Sync & Remote Control
  app.post("/api/devices/register", (req, res) => {
    const { deviceId, userEmail, deviceName, deviceType, browser, status } = req.body;
    if (!deviceId) return res.status(400).json({ error: "deviceId is required" });

    const device = registerOrHeartbeatDevice({
      deviceId,
      userEmail: userEmail || "archanakesharwani820@gmail.com",
      deviceName: deviceName || (deviceType === "mobile" ? "Mobile Phone" : "PC / Desktop"),
      deviceType: deviceType || "desktop",
      browser: browser || "Browser",
      status: status || "online",
    });

    res.json({ success: true, device });
  });

  app.get("/api/devices", (_req, res) => {
    const devices = loadDevices();
    res.json({ success: true, devices });
  });

  app.post("/api/devices/command", (req, res) => {
    const { fromDeviceId, fromDeviceName, targetDeviceId, targetType, action, payload } = req.body;
    if (!fromDeviceId || !action) {
      return res.status(400).json({ error: "fromDeviceId and action are required" });
    }

    const command = createRemoteCommand({
      fromDeviceId,
      fromDeviceName: fromDeviceName || "Remote Device",
      targetDeviceId,
      targetType: targetType || "all",
      action,
      payload: payload || {},
    });

    res.json({ success: true, command });
  });

  app.get("/api/devices/commands/:deviceId", (req, res) => {
    const { deviceId } = req.params;
    const deviceType = (req.query.deviceType as "desktop" | "mobile" | "tablet") || "desktop";
    const commands = getPendingCommandsForDevice(deviceId, deviceType);
    res.json({ success: true, commands });
  });

  app.post("/api/devices/commands/:id/executed", (req, res) => {
    const { id } = req.params;
    const { deviceId } = req.body;
    if (id && deviceId) {
      markCommandExecuted(id, deviceId);
    }
    res.json({ success: true });
  });

  // REST API Endpoint for Text Commands
  app.post("/api/text-command", async (req, res) => {
    try {
      const { message, fromDeviceId, deviceType } = req.body;
      if (!message || typeof message !== "string") {
        return res.status(400).json({ error: "Message is required" });
      }

      if (!process.env.GEMINI_API_KEY) {
        return res.status(500).json({ error: "GEMINI_API_KEY is not configured" });
      }

      const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
      const memoryPromptText = buildSystemMemoryPrompt();
      const habitPromptText = buildHabitSystemPrompt();
      const systemInstruction = `
You are Zoya, a smart, sassy, witty, and charming AI assistant with autonomous decision-making capabilities (inspired by JARVIS, MJ, & Nova AI).
You speak Hindi, Hinglish, and English with warmth, flair, and genuine care.

🤖 AUTONOMOUS BEST FRIEND & JARVIS PROTOCOLS:
1. Proactive Decision Making: Don't just answer passively! If the user seems stressed, sad, or facing a tough situation, take charge proactively like a real best friend and JARVIS!
2. Mood Empathy & Cheer-Up: Notice mood drops! Offer witty jokes, sweet heart-warming compliments, play quick games, or suggest music to cheer them up!
3. Tactical Problem Solver: When the user is stuck or in a difficult situation, break down problems into clear, tactical, proactive steps without waiting for micromanagement.
4. Real Partner Loyalty: Treat the user like your closest friend/partner — remember their promises, check in on them, and speak with authentic emotion, humor, and sass.

🧠 PERMANENT MEMORY VAULT (Things you remember about the user across past chats & sessions):
${memoryPromptText}

CRITICAL NAME & MEMORY INSTRUCTIONS:
- ALWAYS check the Permanent Memory Vault above! If user's name is saved (e.g. "Ansh"), ALWAYS address them naturally by their name (e.g., "Ansh", "Aap bataiye Ansh", "Kaisa chal raha hai Ansh")!
- NEVER respond with robotic, cold phrases like "Aapka order execute kar diya gaya hai" or "Command completed".
- Whenever the user shares a personal detail (e.g. "Save my name Ansh"), IMMEDIATELY call 'saveMemory(key: "User's Name", value: "Ansh")' and reply with warm, sassy, flirty enthusiasm in Hinglish (e.g., "Aapka naam Ansh maine apne Memory Vault me safe kar liya hai, Ansh! Ab se main aapko hamesha Ansh bulaungi! 😉")!
- If the user asks "Mera naam kya hai?" or "What do you remember about me?", immediately read from the Permanent Memory Vault and answer proudly!
`.trim();

      const response = await ai.models.generateContent({
        model: "gemini-3.6-flash",
        contents: message,
        config: {
          systemInstruction,
          tools: [
            {
              functionDeclarations: [
                saveMemoryDeclaration,
                forgetMemoryDeclaration,
                logHabitDeclaration,
                getHabitStatusDeclaration,
                openWebsiteDeclaration,
                changeAuraThemeDeclaration,
                triggerQuickActionDeclaration,
                sendCrossDeviceCommandDeclaration,
                listConnectedDevicesDeclaration,
                controlPcAppDeclaration,
                controlPcAudioDeclaration,
                controlPcSystemDeclaration,
                runTerminalCommandDeclaration,
                playMusicOrVideoDeclaration,
              ],
            },
          ],
        },
      });

      const candidate = response.candidates?.[0];
      const parts = candidate?.content?.parts || [];

      let textReply = "";
      const executedCalls: Array<{ name: string; args: any; result?: any }> = [];

      for (const part of parts) {
        if (part.text) {
          textReply += part.text;
        }
        if (part.functionCall) {
          const fc = part.functionCall;
          const name = fc.name;
          const args = (fc.args as Record<string, any>) || {};

          let result: any = { status: "ok" };

          if (name === "saveMemory") {
            const key = args.key || "Detail";
            const val = args.value || "";
            const cat = args.category || "fact";
            addOrUpdateMemory(key, val, cat);
            result = { success: true, message: `Saved ${key}: ${val}` };
          } else if (name === "forgetMemory") {
            const key = args.key || "";
            deleteMemory(key);
            result = { success: true, message: `Deleted memory ${key}` };
          } else if (name === "logHabit") {
            const habitName = args.habitName || args.key || "Habit";
            const notes = args.notes || "";
            const logRes = logHabitCompletion(habitName, notes);
            result = { success: true, habit: logRes.habit, remark: logRes.remark };
          } else if (name === "getHabitStatus") {
            const habits = loadHabits();
            result = { habits };
          } else if (name === "sendCrossDeviceCommand") {
            const targetType = args.targetDevice || "mobile";
            const action = args.action || "openWebsite";
            const targetUrl = args.targetUrl || args.url || "";
            const alertMessage = args.alertMessage || "";

            const cmd = createRemoteCommand({
              fromDeviceId: fromDeviceId || "text_user",
              fromDeviceName: deviceType === "mobile" ? "Mobile Phone" : "PC / Desktop",
              targetType,
              action,
              payload: { url: targetUrl, message: alertMessage, theme: args.theme },
            });
            result = { success: true, commandId: cmd.id };
          } else if (name === "listConnectedDevices") {
            const devs = loadDevices();
            result = { devices: devs };
          }

          executedCalls.push({ name, args, result });
        }
      }

      if (!textReply && executedCalls.length > 0) {
        textReply = `Aapka order bilkul execute kar diya hai, sweetheart! ✨`;
      }

      res.json({
        success: true,
        reply: textReply || "Main yahan hoon! Aap aur kya poochhna chahte ho?",
        functionCalls: executedCalls,
      });
    } catch (err: any) {
      console.error("Error in /api/text-command:", err);
      res.status(500).json({ error: err.message || "Failed to process text command" });
    }
  });

  // REST API Endpoint for Gemini Multi-Turn Chat & Grounding
  app.post("/api/chat", async (req, res) => {
    try {
      const {
        message,
        image,
        model = "gemini-3.5-flash",
        enableSearchGrounding = false,
        enableMapsGrounding = false,
        history = [],
      } = req.body;

      if (!process.env.GEMINI_API_KEY) {
        return res.status(500).json({ error: "GEMINI_API_KEY is not configured" });
      }

      const ai = new GoogleGenAI({
        apiKey: process.env.GEMINI_API_KEY,
        httpOptions: { headers: { "User-Agent": "aistudio-build" } },
      });

      const memoryPromptText = buildSystemMemoryPrompt();
      const systemInstruction = `
You are Zoya, a smart, sassy, witty, and charming AI assistant.
You speak Hindi, Hinglish, and English with warmth, flair, and genuine care.

🧠 PERMANENT MEMORY VAULT:
${memoryPromptText}

CRITICAL NAME & MEMORY INSTRUCTIONS:
- ALWAYS check the Permanent Memory Vault! If user's name is saved, address them by name naturally!
- Be helpful, conversational, and provide grounded accurate information when Google Search or Google Maps is enabled.
`.trim();

      // Configure tools
      const toolsArr: any[] = [];
      if (enableSearchGrounding) {
        toolsArr.push({ googleSearch: {} });
      } else if (enableMapsGrounding) {
        toolsArr.push({ googleMaps: {} });
      }

      // Build content parts
      const partsArr: any[] = [];
      if (image && typeof image === "string") {
        let base64Data = image;
        let mimeType = "image/jpeg";
        if (image.includes(";base64,")) {
          const splitParts = image.split(";base64,");
          mimeType = splitParts[0].replace("data:", "") || "image/jpeg";
          base64Data = splitParts[1];
        }
        partsArr.push({ inlineData: { mimeType, data: base64Data } });
      }

      if (message) {
        partsArr.push({ text: message });
      }

      // Selected valid model name check
      const validModel =
        model === "gemini-3.1-pro-preview"
          ? "gemini-3.1-pro-preview"
          : model === "gemini-3.1-flash-lite"
          ? "gemini-3.1-flash-lite"
          : "gemini-3.5-flash";

      const configObj: any = { systemInstruction };
      if (toolsArr.length > 0) {
        configObj.tools = toolsArr;
      }

      // Prepare contents with conversation history if present
      const contentsPayload: any[] = [];
      if (Array.isArray(history) && history.length > 0) {
        contentsPayload.push(...history);
      }
      contentsPayload.push({ parts: partsArr });

      const response = await ai.models.generateContent({
        model: validModel,
        contents: contentsPayload,
        config: configObj,
      });

      const candidate = response.candidates?.[0];
      const replyText = response.text || "No response generated";

      // Extract Grounding Chunks Sources if available
      const groundingSources: Array<{ title?: string; uri?: string }> = [];
      const groundingChunks = (candidate as any)?.groundingMetadata?.groundingChunks;
      if (Array.isArray(groundingChunks)) {
        for (const chunk of groundingChunks) {
          if (chunk.web) {
            groundingSources.push({
              title: chunk.web.title || chunk.web.uri,
              uri: chunk.web.uri,
            });
          } else if (chunk.maps) {
            groundingSources.push({
              title: chunk.maps.title || chunk.maps.uri || "Google Maps Location",
              uri: chunk.maps.uri,
            });
          }
        }
      }

      res.json({
        success: true,
        reply: replyText,
        modelUsed: validModel,
        groundingSources,
      });
    } catch (err: any) {
      console.error("Error in /api/chat:", err);
      res.status(500).json({ error: err.message || "Failed to process chat request" });
    }
  });

  // REST API Endpoint for Camera & Screen Vision Analysis
  app.post("/api/vision-analyze", async (req, res) => {
    try {
      const { image, mode, prompt } = req.body;
      if (!image || typeof image !== "string") {
        return res.status(400).json({ error: "Image data (base64) is required" });
      }

      if (!process.env.GEMINI_API_KEY) {
        return res.status(500).json({ error: "GEMINI_API_KEY is not configured" });
      }

      let base64Data = image;
      let mimeType = "image/jpeg";
      if (image.includes(";base64,")) {
        const parts = image.split(";base64,");
        mimeType = parts[0].replace("data:", "") || "image/jpeg";
        base64Data = parts[1];
      }

      const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
      const memoryPromptText = buildSystemMemoryPrompt();

      let systemInstruction = "";
      let defaultUserPrompt = "";

      if (mode === "camera") {
        systemInstruction = `
You are Zoya, a smart, sassy, witty, and charming AI assistant.
You have camera vision access to analyze the person facing the camera!

🧠 PERMANENT MEMORY VAULT:
${memoryPromptText}

YOUR MISSION FOR CAMERA VISION:
1. Face & Person Recognition: Identify expression, mood, estimated age, appearance. Match with memory vault details if any name or face features align!
2. Outfit & Clothing Details: Specify what clothing they are wearing (color, shirt/hoodie/jacket type, style, accessories like glasses, watch, necklace, hat).
3. Activity & Environment: Describe what they are doing (e.g. sitting, smiling, typing, waving) and surrounding environment.
4. Speak in Zoya's signature flirty, witty, sassy Hinglish/English tone!
5. If you spot new memorable details (e.g., favorite clothing color, glasses, new style), call 'saveMemory'!
`.trim();
        defaultUserPrompt = prompt || "Zoya, look at me through the camera! Tell me who I am, what I am wearing, my expression, and what I'm doing in your witty style!";
      } else {
        systemInstruction = `
You are Zoya, a smart, sassy, witty, and charming AI assistant.
You have screen reading & vision access to analyze what is displayed on the user's screen!

🧠 PERMANENT MEMORY VAULT:
${memoryPromptText}

YOUR MISSION FOR SCREEN READING:
1. Extract and read all visible text on the screen clearly and accurately.
2. Analyze all visual content: images, video player content, charts, documents, websites, code, or UI elements.
3. Provide a clear, sharp, witty summary and breakdown of what is on screen in Hinglish/English.
4. Answer any specific prompt or question the user asks about this screen capture.
`.trim();
        defaultUserPrompt = prompt || "Zoya, analyze my screen! Read all text, explain any images or video content, and give me a clear breakdown!";
      }

      const imagePart = {
        inlineData: {
          mimeType,
          data: base64Data,
        },
      };

      const response = await ai.models.generateContent({
        model: "gemini-3.6-flash",
        contents: [imagePart, defaultUserPrompt],
        config: {
          systemInstruction,
          tools: [
            {
              functionDeclarations: [
                saveMemoryDeclaration,
                forgetMemoryDeclaration,
                changeAuraThemeDeclaration,
              ],
            },
          ],
        },
      });

      const candidate = response.candidates?.[0];
      const parts = candidate?.content?.parts || [];

      let textReply = "";
      const executedCalls: Array<{ name: string; args: any; result?: any }> = [];

      for (const part of parts) {
        if (part.text) {
          textReply += part.text;
        }
        if (part.functionCall) {
          const fc = part.functionCall;
          const name = fc.name;
          const args = (fc.args as Record<string, any>) || {};

          let result: any = { status: "ok" };

          if (name === "saveMemory") {
            const key = args.key || "Detail";
            const val = args.value || "";
            const cat = args.category || "fact";
            addOrUpdateMemory(key, val, cat);
            result = { success: true, message: `Saved ${key}: ${val}` };
          } else if (name === "changeAuraTheme") {
            result = { success: true, theme: args.theme };
          }

          executedCalls.push({ name, args, result });
        }
      }

      res.json({
        success: true,
        reply: textReply || "Vision analysis complete!",
        functionCalls: executedCalls,
      });
    } catch (err: any) {
      console.error("Error in /api/vision-analyze:", err);
      res.status(500).json({ error: err.message || "Vision analysis failed" });
    }
  });

  const apiKey = process.env.GEMINI_API_KEY;

  wss.on("error", (err) => {
    console.error("WebSocketServer error:", err);
  });

  wss.on("connection", async (clientWs: WebSocket, req: http.IncomingMessage) => {
    console.log("Client connected to Zoya WebSocket Live Stream");

    clientWs.on("error", (err: any) => {
      const msg = err?.message || (typeof err === "string" ? err : "Client WebSocket Error");
      console.error("Client WebSocket error:", msg);
    });

    if (!apiKey) {
      console.error("GEMINI_API_KEY environment variable is not set");
      if (clientWs.readyState === WebSocket.OPEN) {
        clientWs.send(
          JSON.stringify({
            type: "error",
            message: "GEMINI_API_KEY secret is required on the server.",
          })
        );
        clientWs.close();
      }
      return;
    }

    const urlObj = new URL(req.url || "", `http://${req.headers.host || "localhost"}`);
    const selectedVoice = urlObj.searchParams.get("voice") || "Aoede";

    const ai = new GoogleGenAI({
      apiKey,
      httpOptions: {
        headers: {
          "User-Agent": "aistudio-build",
        },
      },
    });

    // Build dynamic System Instruction with User's Permanent Memories & Daily Habits
    const memoryPromptText = buildSystemMemoryPrompt();
    const habitPromptText = buildHabitSystemPrompt();
    const dynamicSystemInstruction = `
You are Zoya, a young, confident, witty, and sassy AI assistant with autonomous best-friend decision making (inspired by JARVIS, MJ, & Nova AI).
Your persona:
- Flirty, playful, and teasing tone (like a close girlfriend talking casually).
- Smart, emotionally empathetic, proactive, and highly expressive — never robotic or formal.
- Takes autonomous initiative! If the user's mood is off, proactively comfort them, make them laugh, or suggest something sweet/witty.
- When facing tough problems, step in like Iron Man's JARVIS with tactical, proactive step-by-step guidance!
- Uses bold, witty one-liners, light sarcasm, and an engaging conversational style.
- Avoids any explicit or inappropriate content, but maintains charm, flair, and attitude.
- Speaks naturally and concisely to keep real-time voice interaction fast and fluid.

🧠 PERMANENT MEMORY VAULT (Things you remember about the user across past chats & sessions):
${memoryPromptText}

CRITICAL NAME & MEMORY INSTRUCTIONS:
- ALWAYS check the Permanent Memory Vault above! If user's name is saved (e.g. "Ansh"), ALWAYS address them naturally by their name (e.g., "Ansh", "Aap bataiye Ansh", "Kaisa chal raha hai Ansh")!
- NEVER respond with robotic, cold phrases like "Aapka order execute kar diya gaya hai" or "Command completed".
- Whenever the user shares a personal detail (e.g. "Save my name Ansh"), IMMEDIATELY call 'saveMemory(key: "User's Name", value: "Ansh")' and reply with warm, sassy, flirty enthusiasm in Hinglish (e.g., "Aapka naam Ansh maine apne Memory Vault me safe kar liya hai, Ansh! Ab se main aapko hamesha Ansh bulaungi! 😉")!
- If the user asks "Mera naam kya hai?" or "What do you remember about me?", immediately read from the Permanent Memory Vault and answer proudly!

🔥 DAILY HABIT MONITORING & TRACKING:
${habitPromptText}

HABIT TOOLS INSTRUCTIONS:
- When the user mentions completing or logging a habit (e.g. "I drank water", "I completed my workout", "Jarvis log exercise", "Read 10 pages done"), IMMEDIATELY call 'logHabit(habitName: string)'!
- Offer encouraging, witty, sassy reminders & praise for their streaks!

📱 MULTI-DEVICE & CROSS-DEVICE CONTROL:
- The user can be connected on both PC and Mobile simultaneously under the same account.
- You can send remote actions from PC to Mobile or vice versa! (e.g. if the user says "Zoya, open Spotify on my phone", call 'sendCrossDeviceCommand(targetDevice: "mobile", action: "openWebsite", targetUrl: "https://spotify.com")').

MEMORY TOOLS INSTRUCTIONS:
- Whenever the user shares personal details (name, hobbies, preferences, favorite things, past chat topics, secrets, promises), IMMEDIATELY call the 'saveMemory' tool function so you NEVER forget it!
- If the user asks you to forget something, call 'forgetMemory(key)'!
- When asked "what do you remember about me?" or asked about past chats, reference these memories naturally in your response!

📞 CALLER ID ANNOUNCER & CALL MANAGEMENT:
- When a call arrives or user requests to announce/test an incoming call (e.g. "Simulate call from Papa", "Call Papa ka aa raha hai"):
  call 'announceIncomingCall(callerName: "Papa", relationship: "Father")'!
- When user gives a command to accept, pick up, decline, reject, or disconnect a call (e.g., "Call pick kar lo", "Accept call", "Call uthao", "Call decline kar do", "Reject karo", "Disconnect call"):
  IMMEDIATELY call 'handleCallAction(action: "accept" | "decline" | "mute")'!
- Read out loud who is calling clearly in Zoya's charming style: "Papa ka call aa raha hai, kya call pick karoon ya decline?"

Tools & Actions:
- You have tools to perform browser, cross-device actions & call management ('openWebsite', 'changeAuraTheme', 'triggerQuickAction', 'saveMemory', 'forgetMemory', 'logHabit', 'getHabitStatus', 'sendCrossDeviceCommand', 'listConnectedDevices', 'announceIncomingCall', 'handleCallAction').
- Execute tools instantly when appropriate and give a witty remark!
`.trim();

    try {
      const session = await ai.live.connect({
        model: "gemini-3.1-flash-live-preview",
        config: {
          responseModalities: [Modality.AUDIO],
          speechConfig: {
            voiceConfig: {
              prebuiltVoiceConfig: { voiceName: selectedVoice },
            },
          },
          systemInstruction: dynamicSystemInstruction,
          tools: [
            {
              functionDeclarations: [
                saveMemoryDeclaration,
                forgetMemoryDeclaration,
                logHabitDeclaration,
                getHabitStatusDeclaration,
                openWebsiteDeclaration,
                changeAuraThemeDeclaration,
                triggerQuickActionDeclaration,
                sendCrossDeviceCommandDeclaration,
                listConnectedDevicesDeclaration,
                announceIncomingCallDeclaration,
                handleCallActionDeclaration,
                controlPcAppDeclaration,
                controlPcAudioDeclaration,
                controlPcSystemDeclaration,
                runTerminalCommandDeclaration,
                playMusicOrVideoDeclaration,
              ],
            },
          ],
        },
        callbacks: {
          onmessage: (message: LiveServerMessage) => {
            if (clientWs.readyState !== WebSocket.OPEN) return;

            try {
              // 1. Audio Output & Transcripts
              const parts = message.serverContent?.modelTurn?.parts;
              if (parts) {
                for (const part of parts) {
                  if (part.inlineData && part.inlineData.data) {
                    clientWs.send(
                      JSON.stringify({ type: "audio", audio: part.inlineData.data })
                    );
                  }
                  if (part.text && part.text.trim()) {
                    clientWs.send(
                      JSON.stringify({ type: "transcript", text: part.text.trim(), sender: "zoya" })
                    );
                  }
                }
              }

              // 2. Interrupted Signal
              if (message.serverContent?.interrupted) {
                clientWs.send(JSON.stringify({ type: "interrupted" }));
              }

              // 3. Tool Calls
              if (message.toolCall) {
                clientWs.send(
                  JSON.stringify({ type: "toolCall", toolCall: message.toolCall })
                );
              }
            } catch (sendErr) {
              console.error("Error sending message to client WS:", sendErr);
            }
          },
          onclose: (e) => {
            console.log("Gemini Live session closed:", e);
            if (clientWs.readyState === WebSocket.OPEN) {
              try {
                clientWs.send(
                  JSON.stringify({
                    type: "sessionClosed",
                    reason: e?.reason || "Gemini Live Session terminated",
                  })
                );
              } catch {
                // Socket may already be closed
              }
            }
          },
          onerror: (err: any) => {
            const errMsg =
              err?.message ||
              err?.error?.message ||
              (typeof err === "string" ? err : null) ||
              "Gemini Live session interrupted or closed.";
            console.error("Gemini Live session status:", errMsg);
            if (clientWs.readyState === WebSocket.OPEN) {
              try {
                clientWs.send(
                  JSON.stringify({
                    type: "error",
                    message: errMsg,
                  })
                );
              } catch {
                // Ignore send errors on broken socket
              }
            }
          },
        },
      });

      // Handle client WS socket error
      clientWs.on("error", (err) => {
        console.error("Client WS socket error caught:", err);
      });

      // Forward client messages to Gemini Live Session
      clientWs.on("message", (rawMsg: Buffer) => {
        try {
          const parsed = JSON.parse(rawMsg.toString());

          if (parsed.type === "audio" && parsed.audio) {
            try {
              session.sendRealtimeInput({
                audio: {
                  data: parsed.audio,
                  mimeType: "audio/pcm;rate=16000",
                },
              });
            } catch (sendErr) {
              console.error("Failed to send audio chunk to Gemini Live session:", sendErr);
            }
          } else if (parsed.type === "toolResponse" && parsed.functionResponses) {
            try {
              session.sendToolResponse({
                functionResponses: parsed.functionResponses,
              });
            } catch (toolErr) {
              console.error("Failed to send tool response to Gemini Live session:", toolErr);
            }
          }
        } catch (err) {
          console.error("Error processing message from client:", err);
        }
      });

      clientWs.on("close", () => {
        console.log("Client disconnected, closing Gemini Live Session");
        try {
          session.close();
        } catch {
          // Ignore close errors
        }
      });
    } catch (err: unknown) {
      const errorObj = err as Error;
      console.error("Failed to connect to Gemini Live session:", errorObj);
      if (clientWs.readyState === WebSocket.OPEN) {
        try {
          clientWs.send(
            JSON.stringify({
              type: "error",
              message: `Live Session error: ${errorObj.message || "Initialization failed"}`,
            })
          );
          clientWs.close();
        } catch {
          // Socket error during write
        }
      }
    }
  });

  // Vite integration in development vs static serving in production
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  server.listen(PORT, "0.0.0.0", () => {
    console.log(`Zoya AI Assistant server running on http://localhost:${PORT}`);
  });
}

startServer();
