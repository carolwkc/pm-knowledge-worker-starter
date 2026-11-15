export function evidenceSpan(
  text: string,
  start: number,
  end: number,
  excerpt: string,
): { before: string; quote: string; after: string } | null {
  const points = Array.from(text);
  if (
    !Number.isInteger(start) ||
    !Number.isInteger(end) ||
    start < 0 ||
    end <= start ||
    end > points.length
  )
    return null;
  const quote = points.slice(start, end).join('');
  if (quote !== excerpt) return null;
  return { before: points.slice(0, start).join(''), quote, after: points.slice(end).join('') };
}
