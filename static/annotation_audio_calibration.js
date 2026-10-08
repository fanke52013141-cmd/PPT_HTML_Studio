// Audio-only calibration UI; never used to redraw slide content.
(function (root) {
  'use strict';
  function attach({audio, canvas, status, initialTime = 0, markers = []}) {
    let disposed = false, peaks = null, duration = 0;
    const abort = new AbortController();
    const timeout = setTimeout(() => abort.abort(), 30000);
    const context = canvas.getContext('2d');
    function draw() {
      if (disposed || !context) return;
      const width = canvas.width, height = canvas.height;
      context.clearRect(0, 0, width, height);
      context.fillStyle = '#777';
      if (peaks) peaks.forEach((peak, i) => {
        const h = Math.max(1, peak * (height - 8));
        context.fillRect(i * width / peaks.length, (height - h) / 2, 1, h);
      });
      if (duration > 0) {
        markers.forEach(marker => {
          if (!Number.isFinite(marker.start) || marker.start < 0 || marker.start >= duration) return;
          context.fillStyle = marker.color || '#777';
          if (Number.isFinite(marker.end) && marker.end > marker.start)
            context.fillRect(marker.start / duration * width, height - 5,
              (Math.min(duration, marker.end) - marker.start) / duration * width, 5);
          context.fillRect(marker.start / duration * width, 0, 1, height);
        });
        context.fillStyle = '#f46a38';
        context.fillRect(audio.currentTime / duration * width, 0, 2, height);
      }
      status.textContent = `${audio.currentTime.toFixed(3)} 秒${duration ? ' / ' + duration.toFixed(3) + ' 秒' : ''}`;
    }
    function restorePosition() {
      if (Number.isFinite(initialTime) && Number.isFinite(audio.duration) && audio.duration > 0) {
        audio.currentTime = Math.max(0, Math.min(audio.duration - .001, initialTime));
        duration = audio.duration;
        draw();
      }
    }
    function seek(event) {
      if (!Number.isFinite(audio.duration) || audio.duration <= 0) return;
      audio.pause();
      const rect = canvas.getBoundingClientRect();
      audio.currentTime = Math.max(0, Math.min(audio.duration - .001,
        (event.clientX - rect.left) / rect.width * audio.duration));
      draw();
    }
    canvas.addEventListener('click', seek);
    audio.addEventListener('timeupdate', draw);
    audio.addEventListener('seeked', draw);
    audio.addEventListener('loadedmetadata', restorePosition);
    if (audio.readyState >= 1) restorePosition();
    async function load() {
      let decoder;
      try {
        const response = await fetch(audio.currentSrc || audio.src, {signal: abort.signal});
        if (!response.ok) throw Error('audio unavailable');
        if (Number(response.headers.get('Content-Length')) > 64 * 1024 * 1024) throw Error('audio too large');
        const bytes = await response.arrayBuffer();
        if (bytes.byteLength > 64 * 1024 * 1024) throw Error('audio too large');
        if (disposed) return;
        decoder = new (root.AudioContext || root.webkitAudioContext)();
        const buffer = await decoder.decodeAudioData(bytes);
        if (disposed) return;
        duration = buffer.duration;
        const data = buffer.getChannelData(0), count = 800;
        peaks = Array.from({length: count}, (_, i) => {
          let peak = 0;
          for (let j = Math.floor(i * data.length / count); j < Math.floor((i + 1) * data.length / count); j++)
            peak = Math.max(peak, Math.abs(data[j]));
          return peak;
        });
        draw();
      } catch (error) {
        if (!disposed) status.textContent = '波形暂不可用，可继续用播放器试听定位。';
      } finally { clearTimeout(timeout); if (decoder) await decoder.close(); }
    }
    load();
    return () => {
      disposed = true; clearTimeout(timeout); abort.abort(); audio.pause();
      canvas.removeEventListener('click', seek);
      audio.removeEventListener('timeupdate', draw); audio.removeEventListener('seeked', draw);
      audio.removeEventListener('loadedmetadata', restorePosition);
    };
  }
  root.AnnotationAudioCalibration = {attach};
})(typeof window !== 'undefined' ? window : globalThis);
