// Find a quote inside stored text, so exactly that sentence can be highlighted.
// Spacing is ignored, as in the server's quote check, because PDF text moves it
// around. Case is kept. Returns [start, end) in `text`, or null.

export function locateQuote(text: string, quote: string): [number, number] | null {
  const positions: number[] = [];
  let squeezed = "";
  for (let index = 0; index < text.length; index += 1) {
    const char = text.charAt(index);
    if (!/\s/.test(char)) {
      positions.push(index);
      squeezed += char;
    }
  }
  const wanted = quote.replace(/\s/g, "");
  if (!wanted) return null;
  const found = squeezed.indexOf(wanted);
  if (found < 0) return null;
  const start = positions[found];
  const last = positions[found + wanted.length - 1];
  return start === undefined || last === undefined ? null : [start, last + 1];
}
