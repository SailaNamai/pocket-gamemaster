// static/js/story_parameters_file.js
document.addEventListener('DOMContentLoaded', () => {
  const saveBtn = document.getElementById('save-parameters');
  const loadBtn = document.getElementById('load-parameters');

  if (!saveBtn && !loadBtn) {
    console.warn('No save or load buttons found in DOM.');
    return;
  }

  const fields = [
    'param-style',
    'param-world',
    'param-rules',
    'param-player',
    'param-characters'
  ];

  function buildTextPayload() {
    const lines = [];
    lines.push('# Story preset');
    lines.push('# Keep the tags intact');
    lines.push('');
    for (const id of fields) {
      const el = document.getElementById(id);
      const content = el ? String(el.value) : '';
      lines.push(`<${id}>`);
      if (content === '') {
        lines.push('');
      } else {
        lines.push(...content.split(/\r?\n/));
      }
      lines.push(`</${id}>`);
      lines.push('');
    }
    return lines.join('\n') + '\n';
  }

  function sanitizeFilename(name) {
    if (!name) return 'my-preset.txt';
    name = String(name).trim();
    if (!name) return 'my-preset.txt';
    name = name.replace(/[^a-zA-Z0-9\-_.]/g, '_').replace(/^_+|_+$/g, '');
    if (!/\.(txt|preset)$/i.test(name)) name += '.txt';
    return name;
  }

  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      const payload = buildTextPayload();
      let filename = window.prompt('Choose a filename for this preset (no extension):', 'my-preset');
      if (filename === null) return;
      filename = sanitizeFilename(filename);

      const blob = new Blob([payload], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });
  }

  if (loadBtn) {
    loadBtn.addEventListener('click', () => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.txt,text/plain';
      input.addEventListener('change', () => {
        const file = input.files && input.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
          try {
            let text = String(reader.result || '');
            // drop UTF-8 BOM if present
            if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);

            const map = {};
            const lines = text.split(/\r?\n/);

            let currentTag = null;
            const buffer = [];

            // allow optional spaces inside tag lines, e.g. "<param-style>" or "< param-style >"
            const openRe = /^\s*<\s*([a-zA-Z0-9\-_]+)\s*>\s*$/;
            const closeRe = /^\s*<\/\s*([a-zA-Z0-9\-_]+)\s*>\s*$/;

            for (let i = 0; i < lines.length; i++) {
              const line = lines[i];
              const openMatch = line.match(openRe);
              const closeMatch = line.match(closeRe);

              if (openMatch) {
                currentTag = openMatch[1];
                buffer.length = 0;
                continue;
              } else if (closeMatch) {
                const tag = closeMatch[1];
                if (currentTag === tag) {
                  // preserve exact text between tags including empty string
                  map[tag] = buffer.join('\n');
                }
                currentTag = null;
                buffer.length = 0;
                continue;
              } else if (currentTag) {
                buffer.push(line);
              } else {
                // skip non-tag lines (comments, blank lines)
              }
            }

            for (const id of fields) {
              const el = document.getElementById(id);
              if (!el) continue;
              if (Object.prototype.hasOwnProperty.call(map, id)) {
                // always overwrite with parsed value (may be empty string)
                el.value = map[id];
                // dispatch a real InputEvent and a Change event so listeners notice
                const inputEv = new InputEvent('input', { bubbles: true, cancelable: true });
                el.dispatchEvent(inputEv);
                const changeEv = new Event('change', { bubbles: true });
                el.dispatchEvent(changeEv);
              }
            }
          } catch (e) {
            console.error('Failed to load preset file:', e);
            alert('Failed to load preset: invalid or unreadable file.');
          }
        };
        reader.readAsText(file, 'utf-8');
      });
      input.click();
    });
  }
});
