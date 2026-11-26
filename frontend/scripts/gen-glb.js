const { writeFileSync } = require('fs');
const path = require('path');
const header = Buffer.from('glTF');
const version = Buffer.alloc(4);
version.writeUInt32LE(2, 0);
const json = JSON.stringify({
  scene: 0,
  scenes: [{ nodes: [0] }],
  nodes: [{ name: 'Stella', mesh: 0 }],
  meshes: [{
    primitives: [{ attributes: { POSITION: 0 }, indices: 1, material: 0, mode: 4 }]
  }],
  accessors: [
    { bufferView: 0, componentType: 5126, count: 3, type: 'VEC3', max: [1,1,1], min: [-1,-1,-1] },
    { bufferView: 1, componentType: 5123, count: 3, type: 'SCALAR' }
  ],
  bufferViews: [
    { buffer: 0, byteLength: 36 },
    { buffer: 0, byteOffset: 36, byteLength: 12 }
  ],
  buffers: [{ byteLength: 48 }],
  materials: [{ pbrMetallicRoughness: { baseColorFactor: [0, 1, 0.5, 1] } }]
});
const jsonBuf = Buffer.from(json, 'utf8');
const jsonPadding = (4 - (jsonBuf.length % 4)) % 4;
const jsonChunk = Buffer.concat([
  Buffer.alloc(4),
  Buffer.from([0x4E, 0x4F, 0x53, 0x4A]),
  jsonBuf,
  Buffer.alloc(jsonPadding)
]);
const binPadding = (4 - (12 % 4)) % 4;
const binData = Buffer.alloc(12 + binPadding);
const binChunk = Buffer.concat([
  Buffer.alloc(4),
  Buffer.from([0x00, 0x4E, 0x49, 0x42]),
  binData
]);
const totalLength = 12 + jsonChunk.length + binChunk.length;
const lenBuf = Buffer.alloc(4);
lenBuf.writeUInt32LE(totalLength, 0);
const glb = Buffer.concat([header, version, lenBuf, jsonChunk, binChunk]);
writeFileSync(require('path').join(__dirname, '..', 'public', 'models', 'stella.glb'), glb);
console.log('GLB written:', glb.length, 'bytes');