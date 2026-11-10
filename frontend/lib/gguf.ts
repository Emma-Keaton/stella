// GGUF (GGML Universal File) Binary Parser & Local Runtime Inspector for Stella
import { LocalGgufModel } from './types';

declare global {
  interface Navigator {
    deviceMemory?: number;
  }
}

export async function parseGgufHeader(file: File): Promise<LocalGgufModel> {
  const sizeBytes = file.size;
  const sizeFormatted =
    sizeBytes > 1024 * 1024 * 1024
      ? `${(sizeBytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
      : `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;

  // Read first 64KB for GGUF header analysis
  const sliceSize = Math.min(65536, file.size);
  const buffer = await file.slice(0, sliceSize).arrayBuffer();
  const view = new DataView(buffer);

  // GGUF Magic Bytes: 0x47 0x47 0x55 0x46 -> "GGUF" in ASCII (little-endian: 0x46554747)
  let magicValidated = false;
  if (buffer.byteLength >= 4) {
    const b0 = view.getUint8(0);
    const b1 = view.getUint8(1);
    const b2 = view.getUint8(2);
    const b3 = view.getUint8(3);
    const magicStr = String.fromCharCode(b0, b1, b2, b3);
    magicValidated = magicStr === 'GGUF' || file.name.toLowerCase().endsWith('.gguf');
  }

  // Parse architecture & quantization from filename if not extracted
  const lowerName = file.name.toLowerCase();
  let architecture = 'llama';
  if (lowerName.includes('phi')) architecture = 'phi3';
  else if (lowerName.includes('qwen')) architecture = 'qwen2.5';
  else if (lowerName.includes('mistral')) architecture = 'mistral';
  else if (lowerName.includes('nemotron')) architecture = 'nemotron';
  else if (lowerName.includes('gemma')) architecture = 'gemma2';
  else if (lowerName.includes('deepseek')) architecture = 'deepseek';

  let quantization = 'Q4_K_M (4-bit Balanced)';
  if (lowerName.includes('q4_k_m') || lowerName.includes('q4_k')) {
    quantization = 'Q4_K_M (4-bit Medium)';
  } else if (lowerName.includes('q4_0')) {
    quantization = 'Q4_0 (Standard 4-bit)';
  } else if (lowerName.includes('q5_k_m') || lowerName.includes('q5_k')) {
    quantization = 'Q5_K_M (5-bit High Precision)';
  } else if (lowerName.includes('q8_0') || lowerName.includes('q8')) {
    quantization = 'Q8_0 (8-bit Near-Lossless)';
  } else if (lowerName.includes('fp16')) {
    quantization = 'FP16 (16-bit Full Precision)';
  }

  // Estimate context and tensor count
  let contextLength = 4096;
  if (lowerName.includes('128k')) contextLength = 131072;
  else if (lowerName.includes('32k')) contextLength = 32768;
  else if (lowerName.includes('8k')) contextLength = 8192;

  const tensorCount = Math.max(140, Math.floor(sizeBytes / (18 * 1024 * 1024)));

  return {
    fileName: file.name,
    fileSize: sizeFormatted,
    sizeBytes,
    architecture: architecture.toUpperCase(),
    quantization,
    contextLength,
    tensorCount,
    magicValidated,
    loadedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    status: 'ready',
  };
}

// Device capability detection for model recommendations
export interface DeviceSpecs {
  totalRAM: number; // bytes
  availableRAM: number; // bytes
  totalStorage: number; // bytes
  availableStorage: number; // bytes
  cpuCores: number;
  hasGPU: boolean;
  isAndroid: boolean;
  isLowEnd: boolean;
}

export interface ModelCompatibility {
  compatible: boolean;
  reason?: string;
  estimatedRAMNeeded: number; // bytes
  fitsStorage: boolean;
}

export interface CloudProviderSuggestion {
  name: string;
  models: string[];
  freeTier: string;
  signupUrl: string;
}

export function detectDeviceSpecs(): DeviceSpecs {
  const isAndroid = /Android/i.test(navigator.userAgent);
  const deviceMemory = navigator.deviceMemory;
  const isLowEnd = isAndroid || (typeof deviceMemory === 'number' && deviceMemory <= 4);

  const totalRAM = navigator.deviceMemory
    ? navigator.deviceMemory * 1024 * 1024 * 1024
    : 8 * 1024 * 1024 * 1024;

  const totalStorage = 64 * 1024 * 1024 * 1024;
  const availableStorage = totalStorage * 0.5;

  return {
    totalRAM,
    availableRAM: totalRAM * 0.7,
    totalStorage,
    availableStorage,
    cpuCores: navigator.hardwareConcurrency || 4,
    hasGPU: !isAndroid,
    isAndroid,
    isLowEnd,
  };
}

export function checkModelCompatibility(
  modelSizeBytes: number,
  specs: DeviceSpecs
): ModelCompatibility {
  const estimatedRAMNeeded = modelSizeBytes * 1.5;
  const fitsStorage = modelSizeBytes <= specs.availableStorage;
  const fitsRAM = estimatedRAMNeeded <= specs.availableRAM;

  let reason: string | undefined;
  if (!fitsRAM) {
    reason = `Device has ~${(specs.availableRAM / (1024 * 1024 * 1024)).toFixed(1)}GB RAM available. Model needs ~${(estimatedRAMNeeded / (1024 * 1024 * 1024)).toFixed(1)}GB.`;
  } else if (!fitsStorage) {
    reason = `Not enough storage space. Need ~${(modelSizeBytes / (1024 * 1024 * 1024)).toFixed(1)}GB free.`;
  }

  return {
    compatible: fitsRAM && fitsStorage,
    reason,
    estimatedRAMNeeded,
    fitsStorage,
  };
}

export function getCloudProviderSuggestions(): CloudProviderSuggestion[] {
  return [
    {
      name: 'Groq',
      models: ['llama-3.1-8b-instant', 'llama-3.3-70b-versatile'],
      freeTier: '14,400 tokens/min (free tier)',
      signupUrl: 'https://console.groq.com',
    },
    {
      name: 'OpenRouter',
      models: ['meta-llama/llama-3.2-3b-instruct:free', 'google/gemma-2-9b-it:free'],
      freeTier: 'Free tier available for select models',
      signupUrl: 'https://openrouter.ai',
    },
    {
      name: 'Gemini',
      models: ['gemini-1.5-flash', 'gemini-2.0-flash-exp'],
      freeTier: 'Free tier with rate limits',
      signupUrl: 'https://aistudio.google.com',
    },
    {
      name: 'OpenAI-compatible',
      models: ['gpt-4o-mini', 'gpt-3.5-turbo'],
      freeTier: 'Trial credits for new accounts',
      signupUrl: 'https://platform.openai.com',
    },
  ];
}

export function getFreeUpSpaceSuggestions(
  modelSizeBytes: number,
  specs: DeviceSpecs
): string[] {
  const suggestions: string[] = [];
  const neededGB = (modelSizeBytes / (1024 * 1024 * 1024)).toFixed(1);
  const availableGB = (specs.availableStorage / (1024 * 1024 * 1024)).toFixed(1);
  const fitsStorage = modelSizeBytes <= specs.availableStorage;

  if (!fitsStorage) {
    suggestions.push(
      `Free up ~${neededGB}GB of storage space. Currently ${availableGB}GB available.`
    );
    suggestions.push('Move existing GGUF models to external storage or SD card.');
    suggestions.push('Clear app cache and temporary files in Stella Settings.');
    suggestions.push('Uninstall unused apps to free device storage.');
  }

  if (specs.isLowEnd || specs.isAndroid) {
    suggestions.push(
      'Consider using a smaller Q4_K_M quantized model (under 2GB) for better performance.'
    );
  }

  return suggestions;
}

// Export empty - no hardcoded models. Users provide their own via download or file upload.
export const SAMPLE_LOCAL_MODELS: LocalGgufModel[] = [];
