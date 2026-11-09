'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';

export default function App() {
  const [theme] = useState('solar');

  return (
    <div className='min-h-screen bg-slate-900 text-white p-8'>
      <h1 className='text-3xl font-bold mb-4'>Stella</h1>
      <p className='text-gray-400 mb-8'>Your on-device AI assistant</p>
      <motion.div
        whileHover={{ scale: 1.05 }}
        className='p-6 bg-slate-800 rounded-xl inline-block'
      >
        <button className='text-blue-400'>Test Motion</button>
      </motion.div>
    </div>
  );
}