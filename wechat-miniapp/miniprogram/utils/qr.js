const qrcode = require('../vendor/qrcode');
const theme = require('./theme');

function draw(page, selector, payload, options) {
  const value = String(payload || '');
  if (!value) return Promise.reject(new Error('二维码内容为空'));
  const settings = {
    dark: theme.current().ink,
    light: '#FAF8F2',
    correction: 'M',
    ...options,
  };
  return new Promise((resolve, reject) => {
    wx.createSelectorQuery()
      .in(page)
      .select(selector)
      .fields({ node: true, size: true })
      .exec((rows) => {
        const target = rows && rows[0];
        if (!target || !target.node || !target.width || !target.height) {
          reject(new Error('二维码画布尚未准备好'));
          return;
        }
        try {
          const code = qrcode(0, settings.correction);
          code.addData(value, 'Byte');
          code.make();
          const canvas = target.node;
          const context = canvas.getContext('2d');
          const dpr = wx.getWindowInfo ? wx.getWindowInfo().pixelRatio : 2;
          canvas.width = Math.round(target.width * dpr);
          canvas.height = Math.round(target.height * dpr);
          context.scale(dpr, dpr);
          context.fillStyle = settings.light;
          context.fillRect(0, 0, target.width, target.height);

          const modules = code.getModuleCount();
          const quietModules = 4;
          const cell = Math.max(
            1,
            Math.floor(
              Math.min(target.width, target.height)
                / (modules + quietModules * 2),
            ),
          );
          const rendered = cell * modules;
          const left = Math.floor((target.width - rendered) / 2);
          const top = Math.floor((target.height - rendered) / 2);
          context.fillStyle = settings.dark;
          for (let row = 0; row < modules; row += 1) {
            for (let column = 0; column < modules; column += 1) {
              if (!code.isDark(row, column)) continue;
              context.fillRect(
                left + column * cell,
                top + row * cell,
                cell,
                cell,
              );
            }
          }
          resolve({ modules, cell });
        } catch (error) {
          reject(error);
        }
      });
  });
}

module.exports = { draw };
