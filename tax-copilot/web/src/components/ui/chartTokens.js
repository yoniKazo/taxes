/* Chart colour slots, kept out of Chart.jsx so that file exports only components.
 *
 * Slots 1-3 of the validated categorical order (blue, orange, aqua). Read as CSS
 * custom properties, so dark mode uses steps chosen for the dark surface instead
 * of an automatic flip of the light ones.
 */

export const SERIES_VARS = ['--series-1', '--series-2', '--series-3'];

export function seriesColor(index) {
  return `var(${SERIES_VARS[index % SERIES_VARS.length]})`;
}
