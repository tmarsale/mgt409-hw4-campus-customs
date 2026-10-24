import { useEffect, useRef, useState } from "react";

/**
 * A product photo shown in a frame that matches the photo's own background (Problem 10).
 *
 * The catalogue photos come from different sources: some have white backgrounds, some black,
 * and some are light photos padded with black bars on the sides. Instead of editing the images,
 * the browser reads a tiny copy of each photo once, finds its real background color, and
 *  - paints the frame in that color, so the photo blends into its tile with no visible edges;
 *  - hides any black side bars (clip-path), so letterboxed photos look clean.
 * Nothing is sent anywhere; results are cached per image for the session.
 */

interface Look {
  background: string;
  dark: boolean;
  left: number; // letterbox bar widths, as a percentage of the photo's width
  right: number;
}

const looks = new Map<string, Look>();
const SIZE = 64;

function analyse(img: HTMLImageElement): Look | null {
  try {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = SIZE;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return null;
    ctx.drawImage(img, 0, 0, SIZE, SIZE);
    const data = ctx.getImageData(0, 0, SIZE, SIZE).data;
    const px = (x: number, y: number) => {
      const i = (y * SIZE + x) * 4;
      return [data[i], data[i + 1], data[i + 2]] as const;
    };
    const lum = ([r, g, b]: readonly number[]) => 0.299 * r + 0.587 * g + 0.114 * b;
    const near = (a: readonly number[], b: readonly number[]) => Math.abs(lum(a) - lum(b)) < 28;

    // Length of the run of "corner colored" pixels from one side, on a few rows.
    const corner = px(1, 1);
    const run = (y: number, fromRight: boolean) => {
      let n = 0;
      while (n < SIZE / 3 && near(px(fromRight ? SIZE - 1 - n : n, y), corner)) n++;
      return n;
    };
    const rows = [3, SIZE / 2, SIZE - 4];
    const leftRuns = rows.map((y) => run(y, false));
    const rightRuns = rows.map((y) => run(y, true));
    const steady = (runs: number[]) => Math.max(...runs) - Math.min(...runs) <= 2 && runs[0] >= 2 && runs[0] < SIZE / 3;
    const inside = px(Math.min(leftRuns[2] + 2, SIZE - 1), SIZE - 4);
    // Letterboxed: dark bars of the same width on both sides, with a light photo between them.
    if (lum(corner) < 50 && steady(leftRuns) && steady(rightRuns) && lum(inside) > 200) {
      return {
        background: `rgb(${inside.join(",")})`,
        dark: false,
        left: ((Math.max(...leftRuns) + 1.5) / SIZE) * 100,
        right: ((Math.max(...rightRuns) + 1.5) / SIZE) * 100,
      };
    }
    // Otherwise the corners are the background: average the four of them.
    const corners = [px(1, 1), px(SIZE - 2, 1), px(1, SIZE - 2), px(SIZE - 2, SIZE - 2)];
    const avg = [0, 1, 2].map((c) => Math.round(corners.reduce((s, p) => s + p[c], 0) / 4));
    return { background: `rgb(${avg.join(",")})`, dark: lum(avg) < 90, left: 0, right: 0 };
  } catch {
    return null; // e.g. a cross-origin image: keep the default frame
  }
}

interface Props {
  src: string;
  alt: string;
  className?: string;
  loading?: "lazy" | "eager";
}

export default function ProductImage({ src, alt, className = "", loading = "lazy" }: Props) {
  const [look, setLook] = useState<Look | undefined>(() => looks.get(src));
  const imgRef = useRef<HTMLImageElement>(null);

  const measure = () => {
    const img = imgRef.current;
    if (!img || !img.complete || !img.naturalWidth) return;
    let found = looks.get(src);
    if (!found) {
      const result = analyse(img);
      if (!result) return;
      looks.set(src, result);
      found = result;
    }
    setLook(found);
  };

  // Cached images can finish loading before React attaches onLoad.
  useEffect(() => {
    setLook(looks.get(src));
    measure();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [src]);

  const clip = look && (look.left || look.right) ? `inset(0 ${look.right}% 0 ${look.left}%)` : undefined;
  return (
    <div
      className={`photo ${look ? "is-ready" : ""} ${look?.dark ? "is-dark" : ""} ${className}`}
      style={look ? { backgroundColor: look.background } : undefined}
    >
      <img ref={imgRef} src={src} alt={alt} loading={loading} onLoad={measure} style={clip ? { clipPath: clip } : undefined} />
    </div>
  );
}
