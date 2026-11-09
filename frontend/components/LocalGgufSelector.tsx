'use client';

import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  HardDrive,
  Upload,
  CheckCircle2,
  Cpu,
  FileCode,
  ShieldCheck,
  Zap,
  Info,
  Trash2,
  Layers,
  Database,
  ArrowRight,
} from 'lucide-react';
import { LocalGgufModel, AssistantTheme } from '@/lib/types';
import { THEME_CONFIGS } from '@/lib/theme';
import { parseGgufHeader, SAMPLE_LOCAL_MODELS } from '@/lib/gguf';
import { StarSpinner } from './StarSpinner';

interface LocalGgufSelectorProps {
  currentModel: LocalGgufModel | null;
  onSelectModel: (model: LocalGgufModel) => void;
  theme: AssistantTheme;
}

export function LocalGgufSelector({
  currentModel,
  onSelectModel,
  theme,
}: LocalGgufSelectorProps) {
  const themeConfig = THEME_CONFIGS[theme] || THEME_CONFIGS.rainbow;
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isLoadingFile, setIsLoadingFile] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await processGgufFile(file);
  };

  const processGgufFile = async (file: File) => {
    setErrorMessage(null);

    if (!file.name.toLowerCase().endsWith('.gguf')) {
      setErrorMessage(
        'Invalid File Format: Please select a valid .gguf model file (e.g. Llama-3.2-3B.Q4_K_M.gguf). GGUF is the universal binary format for local neural execution.'
      );
      return;
    }

    setIsLoadingFile(true);
    try {
      const parsed = await parseGgufHeader(file);
      onSelectModel(parsed);
    } catch (err) {
      setErrorMessage(
        'Could not parse GGUF header. Please ensure the file is not corrupted and is an uncompressed GGUF binary.'
      );
    } finally {
      setIsLoadingFile(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      await processGgufFile(file);
    }
  };

  return (
    <div className="space-y-4">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".gguf"
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Main GGUF Upload Box / Dropzone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`p-6 rounded-2xl border-2 border-dashed transition-all cursor-pointer text-center space-y-3 relative overflow-hidden group ${
          isDragOver
            ? 'bg-cyan-950/40 border-cyan-400 scale-[0.99]'
            : 'bg-[#0f121a] hover:bg-[#131622] hover:border-slate-600'
        }`}
        style={{
          borderColor: isDragOver ? themeConfig.primaryHex : undefined,
        }}
      >
        <div className="flex flex-col items-center justify-center space-y-2">
          <div
            className="w-12 h-12 rounded-2xl flex items-center justify-center border transition-transform group-hover:scale-110"
            style={{
              borderColor: themeConfig.primaryHex + '50',
              background: themeConfig.primaryHex + '15',
              color: themeConfig.primaryHex,
            }}
          >
            {isLoadingFile ? (
              <StarSpinner size="xs" theme={theme} />
            ) : (
              <HardDrive className="w-6 h-6" />
            )}
          </div>

          <div>
            <h4 className="text-sm font-bold text-white">
              {isLoadingFile
                ? 'Inspecting GGUF Binary...'
                : 'Select Local .gguf Model File'}
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              Drag &amp; drop or browse your local storage for any quantized GGUF weights
            </p>
          </div>

          <div className="flex items-center gap-2 pt-1 text-[11px] font-mono text-slate-500">
            <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">
              .gguf files only
            </span>
            <span>&bull;</span>
            <span>Zero cloud uploads</span>
            <span>&bull;</span>
            <span>100% Private</span>
          </div>
        </div>
      </div>

      {/* Friendly Error Banner */}
      {errorMessage && (
        <motion.div
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-600/70 text-rose-300 text-xs leading-relaxed"
        >
          <strong>Notice: </strong>
          {errorMessage}
        </motion.div>
      )}

      {/* Currently Loaded Active GGUF Model Info Card */}
      {currentModel && (
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="p-4 rounded-2xl bg-[#131722] border space-y-3"
          style={{ borderColor: themeConfig.primaryHex + '50' }}
        >
          <div className="flex flex-col gap-2.5">
            {/* Row 1: Icon & Model File Name */}
            <div className="flex items-center gap-2.5 min-w-0">
              <div
                className="w-8 h-8 rounded-xl flex items-center justify-center border shrink-0"
                style={{
                  borderColor: themeConfig.primaryHex + '60',
                  background: themeConfig.primaryHex + '20',
                  color: themeConfig.primaryHex,
                }}
              >
                <Cpu className="w-4 h-4" />
              </div>
              <h4 className="text-xs font-bold text-white truncate min-w-0">
                {currentModel.fileName}
              </h4>
            </div>

            {/* Row 2: GGUF Validated Badge & Change File Action */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-800/60">
              <span
                className="text-[10px] font-semibold px-2.5 py-0.5 rounded-full border flex items-center gap-1 shrink-0"
                style={{
                  color: themeConfig.primaryHex,
                  borderColor: themeConfig.primaryHex + '40',
                  background: themeConfig.primaryHex + '15',
                }}
              >
                <CheckCircle2 className="w-3 h-3" />
                GGUF Validated
              </span>

              <div className="flex items-center gap-3 shrink-0 ml-auto">
                <span className="text-[11px] text-slate-400 font-mono">
                  {currentModel.fileSize} &bull; {currentModel.architecture}
                </span>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="text-xs hover:text-white underline font-semibold transition-colors"
                  style={{ color: themeConfig.primaryHex }}
                >
                  Change File
                </button>
              </div>
            </div>
          </div>

          {/* Metadata Grid */}
          <div className="grid grid-cols-3 gap-2 text-[10px] font-mono pt-1">
            <div className="p-2 rounded-xl bg-[#0b0e14] border border-slate-800 text-slate-300">
              <span className="text-slate-500 block uppercase">Quantization</span>
              <span className="font-semibold text-white">{currentModel.quantization}</span>
            </div>
            <div className="p-2 rounded-xl bg-[#0b0e14] border border-slate-800 text-slate-300">
              <span className="text-slate-500 block uppercase">Context Window</span>
              <span className="font-semibold text-white">{currentModel.contextLength} tokens</span>
            </div>
            <div className="p-2 rounded-xl bg-[#0b0e14] border border-slate-800 text-slate-300">
              <span className="text-slate-500 block uppercase">Tensor Count</span>
              <span className="font-semibold text-white">{currentModel.tensorCount} tensors</span>
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-cyan-950/30 border border-cyan-800/60 text-xs text-cyan-300 flex items-center justify-between">
            <span className="flex items-center gap-1.5 font-medium">
              <Zap className="w-3.5 h-3.5" />
              Serving Mode: On-Device Neural Worker Active
            </span>
            <span className="text-[10px] font-mono text-emerald-400">0ms network latency</span>
          </div>
        </motion.div>
      )}

      {/* Preset Bundled Samples */}
      <div className="space-y-2 pt-1">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1">
          Or Quick-Serve Sample GGUF Profiles
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {SAMPLE_LOCAL_MODELS.map((sample) => {
            const isSelected = currentModel?.fileName === sample.fileName;
            return (
              <button
                key={sample.fileName}
                type="button"
                onClick={() => onSelectModel(sample)}
                className={`p-3 rounded-xl border text-left transition-all ${
                  isSelected
                    ? 'border-cyan-400 bg-cyan-950/40 text-white'
                    : 'bg-[#10121a] border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
                style={{
                  borderColor: isSelected ? themeConfig.primaryHex : undefined,
                  background: isSelected ? themeConfig.primaryHex + '15' : undefined,
                }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white truncate">
                    {sample.fileName.split('-')[0]}
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {sample.fileSize}
                  </span>
                </div>
                <p className="text-[10px] text-slate-400 truncate mt-0.5">
                  {sample.quantization}
                </p>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
