import { useEffect, useRef } from "react";
import { IconWaveSine } from "@tabler/icons-react";

export function Brand() {
  return <span className="brand"><span className="brand-mark"><IconWaveSine size={25} stroke={2.2} /></span>PharmaTrace</span>;
}

/** An abstract thermal field. Draw once per resize and animate its entrance in CSS. */
export function ThermalField() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    function draw() {
      if (!canvas) return;
      const { width, height } = canvas.getBoundingClientRect();
      const scale = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(width * scale);
      canvas.height = Math.round(height * scale);
      const ctx = canvas.getContext("2d");
      if (!ctx || !width || !height) return;
      ctx.scale(scale, scale);
      for (let row = 0; row < 62; row++) {
        const depth = row / 61;
        ctx.beginPath();
        for (let i = 0; i <= 180; i++) {
          const x = i / 180;
          const ridge = Math.exp(-((x - .58 - depth * .18) ** 2) / .046);
          const ripple = Math.sin(x * 8.5 - depth * 3.6);
          const y = .34 + depth * .54 - ridge * (.32 + ripple * .24) + Math.sin(x * 5 + depth * 5) * .11;
          if (i === 0) ctx.moveTo(0, y * height);
          else ctx.lineTo(x * width, y * height);
        }
        ctx.strokeStyle = `rgba(${85 + row}, ${188 + row}, 217, ${.27 + depth * .53})`;
        ctx.lineWidth = .85;
        ctx.stroke();
      }
    }
    const observer = new ResizeObserver(draw);
    observer.observe(canvas);
    return () => observer.disconnect();
  }, []);
  return <canvas className="thermal-field" ref={ref} aria-hidden="true" />;
}
