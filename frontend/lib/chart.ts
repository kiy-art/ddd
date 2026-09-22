/**
 * Monotone cubic Hermite interpolation (Fritsch-Carlson), the same
 * construction as d3's curveMonotoneX - draws a smooth curve through
 * points with x assumed non-decreasing (our chart x is always time).
 *
 * Price history points are recorded at irregular real-world intervals
 * (a burst of admin edits one day, weeks of silence, a daily fetch the
 * next), so x-spacing between points is highly uneven. A naive uniform
 * Catmull-Rom spline (the previous implementation) computes each
 * point's tangent from its neighbors' raw coordinate deltas without
 * accounting for that uneven spacing - with a big y jump between two
 * points that are very close together in x (or, worse, share the same
 * recorded_at day), the resulting control points fly off far outside
 * the segment and the curve loops or bends back on itself instead of
 * running left-to-right. Monotone cubic interpolation constrains each
 * segment's tangents (see the `s > 9` check below) specifically to
 * prevent that overshoot, which is why it's the standard choice for
 * "connect real, unevenly-spaced data points without looking broken".
 */
export function smoothPath(points: { x: number; y: number }[]): string {
  const n = points.length;
  if (n < 2) return "";
  if (n === 2) return `M ${points[0].x} ${points[0].y} L ${points[1].x} ${points[1].y}`;

  const dx: number[] = [];
  const dy: number[] = [];
  const secant: number[] = [];
  for (let i = 0; i < n - 1; i++) {
    dx.push(points[i + 1].x - points[i].x);
    dy.push(points[i + 1].y - points[i].y);
    secant.push(dx[i] === 0 ? 0 : dy[i] / dx[i]);
  }

  const tangent: number[] = new Array(n);
  tangent[0] = secant[0];
  tangent[n - 1] = secant[n - 2];
  for (let i = 1; i < n - 1; i++) {
    const m0 = secant[i - 1];
    const m1 = secant[i];
    if (m0 === 0 || m1 === 0 || (m0 > 0) !== (m1 > 0)) {
      tangent[i] = 0;
    } else {
      const w1 = 2 * dx[i] + dx[i - 1];
      const w2 = dx[i] + 2 * dx[i - 1];
      tangent[i] = (w1 + w2) / (w1 / m0 + w2 / m1);
    }
  }

  // Fritsch-Carlson constraint: keeps each segment's curve from
  // overshooting past its endpoints' y values (the actual cause of the
  // loop/L-shaped-bend artifact).
  for (let i = 0; i < n - 1; i++) {
    const m = secant[i];
    if (m === 0) {
      tangent[i] = 0;
      tangent[i + 1] = 0;
      continue;
    }
    const a = tangent[i] / m;
    const b = tangent[i + 1] / m;
    const s = a * a + b * b;
    if (s > 9) {
      const factor = 3 / Math.sqrt(s);
      tangent[i] = factor * a * m;
      tangent[i + 1] = factor * b * m;
    }
  }

  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 0; i < n - 1; i++) {
    const c1x = points[i].x + dx[i] / 3;
    const c1y = points[i].y + (tangent[i] * dx[i]) / 3;
    const c2x = points[i + 1].x - dx[i] / 3;
    const c2y = points[i + 1].y - (tangent[i + 1] * dx[i]) / 3;
    d += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${points[i + 1].x} ${points[i + 1].y}`;
  }
  return d;
}
