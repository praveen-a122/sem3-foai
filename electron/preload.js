const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('mindSpringApp', {
  platform: process.platform,
  version: '1.0.0',
});
