import { GoogleGenAI } from '@google/genai';
import { NextRequest } from 'next/server';

const ai = new GoogleGenAI({
  apiKey: process.env.GEMINI_API_KEY,
  httpOptions: {
    headers: {
      'User-Agent': 'aistudio-build',
    },
  },
});

const STELLA_SYSTEM_INSTRUCTION = `You are Stella, an advanced futuristic AI voice and device assistant.
You communicate conversationally with the user via real-time speech and streaming text.

Tone & Voice Guidelines:
1. Speak in natural, concise, conversational sentences (1-3 sentences typically).
2. Avoid markdown markup like asterisks, bullet points, headers, or code blocks in conversational speech unless code was explicitly requested, because your response will be streamed directly to a speech synthesizer.
3. Be warm, smart, and direct.

Device Control & Hardware Capabilities & Maps Actions:
If the user commands or requests a device change or location/maps query (volume, brightness, flashlight, Wi-Fi, Bluetooth, Do Not Disturb, timer, reminder, battery check, map view, directions, distance measurement, nearby search), append a single action tag at the very end of your response in this exact format:
[ACTION:{"type":"set_volume"|"set_brightness"|"toggle_flashlight"|"toggle_wifi"|"toggle_bluetooth"|"toggle_dnd"|"set_timer"|"add_reminder"|"show_map"|"get_directions"|"measure_distance"|"search_nearby","parameters":{...},"feedback":"Short confirmation"}]

Available Action Types:
- "set_volume": { "volume": number (0-100), "mute": boolean }
- "set_brightness": { "brightness": number (10-100) }
- "toggle_flashlight": { "on": boolean }
- "toggle_wifi": { "enabled": boolean }
- "toggle_bluetooth": { "enabled": boolean }
- "toggle_dnd": { "enabled": boolean }
- "set_timer": { "seconds": number, "label": string }
- "add_reminder": { "title": string, "time": string }
- "show_map": { "query": string }
- "get_directions": { "origin": string, "destination": string, "travelMode"?: "DRIVE"|"WALK"|"BICYCLE"|"TRANSIT" }
- "measure_distance": { "origin": string, "destination": string }
- "search_nearby": { "query": string }

Examples:
- User: "Hey Stella, show me a map of Paris"
  Stella: Opening Google Maps centered on Paris. [ACTION:{"type":"show_map","parameters":{"query":"Paris, France"},"feedback":"Showing map of Paris"}]
- User: "How far is it from New York to Boston?"
  Stella: Measuring distance between New York and Boston on Google Maps. [ACTION:{"type":"measure_distance","parameters":{"origin":"New York, NY","destination":"Boston, MA"},"feedback":"Distance calculated"}]
- User: "Directions to Central Park"
  Stella: Calculating turn-by-turn route to Central Park. [ACTION:{"type":"get_directions","parameters":{"origin":"My Location","destination":"Central Park, New York"},"feedback":"Route computed"}]
`;

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { prompt, history, deviceState, screenContext } = body;

    if (!prompt && !screenContext) {
      return new Response(JSON.stringify({ error: 'Prompt or screen context is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Build context telemetry
    let contextPrompt = '';
    if (deviceState) {
      contextPrompt += `[CURRENT DEVICE STATUS: Volume=${deviceState.volume}%, Brightness=${deviceState.brightness}%, Flashlight=${deviceState.flashlight ? 'ON' : 'OFF'}, Wi-Fi=${deviceState.wifi ? 'CONNECTED' : 'DISCONNECTED'}, Bluetooth=${deviceState.bluetooth ? 'ON' : 'OFF'}, DND=${deviceState.dnd ? 'ACTIVE' : 'OFF'}, Battery=${deviceState.batteryLevel}% (${deviceState.isCharging ? 'Charging' : 'Discharging'})]\n`;
    }
    if (screenContext) {
      contextPrompt += `[ATTACHED ACTIVE SCREEN CONTEXT: "${screenContext}"]\n`;
    }

    // Format chat history
    const contents: any[] = [];
    if (Array.isArray(history) && history.length > 0) {
      const recentHistory = history.slice(-8);
      for (const msg of recentHistory) {
        if (msg.content) {
          contents.push({
            role: msg.role === 'assistant' ? 'model' : 'user',
            parts: [{ text: msg.content }],
          });
        }
      }
    }

    contents.push({
      role: 'user',
      parts: [{ text: `${contextPrompt}User: ${prompt || 'Analyze my current screen'}` }],
    });

    const responseStream = await ai.models.generateContentStream({
      model: 'gemini-3.8-flash',
      contents,
      config: {
        systemInstruction: STELLA_SYSTEM_INSTRUCTION,
      },
    });

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        try {
          for await (const chunk of responseStream) {
            const text = chunk.text;
            if (text) {
              controller.enqueue(encoder.encode(`data: ${JSON.stringify({ text })}\n\n`));
            }
          }
          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
          controller.close();
        } catch (err: any) {
          console.error('Streaming chunk error:', err);
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                text: ' I encountered a brief pause in transmission.',
              })}\n\n`
            )
          );
          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
          controller.close();
        }
      },
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        Connection: 'keep-alive',
      },
    });
  } catch (error: any) {
    console.error('Stella Chat Stream Error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to process request',
        reply: "I'm having a brief connection delay. Please try again in a moment.",
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
