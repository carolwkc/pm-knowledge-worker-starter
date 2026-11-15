import { describe, expect, it } from 'vitest';
import { evidenceSpan } from './evidence';

describe('evidenceSpan', () => {
  it('uses Python code-point offsets without normalising Unicode or CRLF', () => {
    const text = '👋 Café\r\n\r\nTroubleshooting accélération.\r\n';
    const excerpt = 'Troubleshooting accélération.\r\n';
    const start = Array.from('👋 Café\r\n\r\n').length;
    expect(evidenceSpan(text, start, Array.from(text).length, excerpt)).toEqual({
      before: '👋 Café\r\n\r\n',
      quote: excerpt,
      after: '',
    });
  });
  it.each([
    [-1, 2, 'ab'],
    [0, 99, 'abc'],
    [2, 1, ''],
    [0, 1.5, 'a'],
    [0, 2, 'xx'],
  ])('refuses invalid or mismatched spans (%s, %s)', (start, end, excerpt) => {
    expect(evidenceSpan('abc', start, end, excerpt)).toBeNull();
  });
});
