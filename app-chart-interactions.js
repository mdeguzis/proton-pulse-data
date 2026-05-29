// Common interactive chart helpers. Adds hover-to-trace + click-to-filter
// to any SVG chart that follows the data-point convention below.
//
// The existing chart on stats.html (the multi-year sparkline) already uses
// invisible <rect class="hover-target"> per data point. This module wraps
// that pattern as a reusable helper so game-stats.html and any future chart
// can call attachChartHover() / attachClickToFilter() without duplicating
// boilerplate.
//
// Loaded as a classic script BEFORE the page's chart-rendering scripts so
// the globals (attachChartHover, attachClickToFilter, dispatchFilter) are
// ready at init time. There is no auto-init -- callers wire this up after
// they inject their SVG into the DOM.
//
// HTML contract for a hover-traceable chart:
//   <svg>
//     ...your chart paths...
//     <line class="ci-hover-guide" id="ci-guide-{id}"/>
//     <circle class="ci-hover-dot" id="ci-dot-{id}-pos"/>
//     <circle class="ci-hover-dot ci-neg" id="ci-dot-{id}-neg"/>
//     <rect class="ci-hover-target" data-idx="0" x="..." y="..." width="..." height="..."/>
//     ...one rect per data point...
//   </svg>
//   <div class="ci-tooltip" id="ci-tip-{id}"/>
//
// And in CSS (already in app.css for the existing chart):
//   .ci-hover-target { cursor: pointer; }
//   .ci-hover-guide  { opacity: 0; stroke: rgba(255,255,255,0.18); stroke-dasharray: 3 3; pointer-events: none; }
//   .ci-hover-dot    { opacity: 0; r: 4; fill: #5bd17a; pointer-events: none; }
//   .ci-hover-dot.ci-neg { fill: #ff6b6b; }
//   .ci-host.is-hovered .ci-hover-guide,
//   .ci-host.is-hovered .ci-hover-dot { opacity: 1; }
//   .ci-tooltip { position: absolute; opacity: 0; pointer-events: none; ... }
//   .ci-host.is-hovered .ci-tooltip { opacity: 1; }

// Attach hover behaviour to an already-rendered SVG chart.
//
// opts:
//   svg        : the <svg> element
//   host       : the wrapping element that gets the .is-hovered class
//                (so CSS can show the guide/dot/tooltip in one rule)
//   tooltip    : the tooltip DOM node positioned within `host`
//   guide      : the <line> guide element (optional)
//   dots       : array of <circle> elements positioned to the data point
//   data       : array of data items, one per hover target rect
//   getX       : (idx) => x coordinate in SVG userspace
//   getYForDot : (item, dotIdx) => y coordinate for dots[dotIdx]
//   renderTip  : (item, idx) => innerHTML for the tooltip
//   onClick    : (item, idx) => optional click handler for filtering
function attachChartHover(opts) {
  const {
    svg, host, tooltip, guide, dots = [],
    data, getX, getYForDot, renderTip, onClick,
  } = opts;
  if (!svg || !host || !tooltip || !data || !data.length) return;

  const targets = svg.querySelectorAll('.ci-hover-target');
  targets.forEach(rect => {
    const idx = parseInt(rect.getAttribute('data-idx'), 10);
    const item = data[idx];
    if (item == null) return;

    rect.addEventListener('mouseenter', () => {
      const x = getX(idx);
      if (guide) {
        guide.setAttribute('x1', x);
        guide.setAttribute('x2', x);
      }
      dots.forEach((dot, di) => {
        if (!dot) return;
        dot.setAttribute('cx', x);
        dot.setAttribute('cy', getYForDot(item, di));
      });

      host.classList.add('is-hovered');
      tooltip.innerHTML = renderTip(item, idx);

      // Position the tooltip horizontally aligned with the data point,
      // clamped so it doesn't run off the host's edges
      const hostRect = host.getBoundingClientRect();
      const svgRect = svg.getBoundingClientRect();
      // Use the rect's screen position so the tooltip lines up regardless
      // of the SVG viewBox scaling we set up
      const rectRect = rect.getBoundingClientRect();
      const screenX = (rectRect.left + rectRect.right) / 2 - hostRect.left;
      const tipW = tooltip.offsetWidth || 120;
      let leftPx = screenX - tipW / 2;
      const maxLeft = hostRect.width - tipW - 4;
      if (leftPx < 4) leftPx = 4;
      if (leftPx > maxLeft) leftPx = maxLeft;
      tooltip.style.left = leftPx + 'px';
    });

    rect.addEventListener('mouseleave', () => {
      host.classList.remove('is-hovered');
    });

    if (onClick) {
      rect.addEventListener('click', () => onClick(item, idx));
    }
  });
}

// Wire click-to-filter behaviour on any element matching a CSS selector.
// On click, dispatches a 'chart-filter' CustomEvent on the document so the
// page-level filter listener can update the list below.
//
// opts:
//   root      : ancestor to query within (defaults to document)
//   selector  : CSS selector for clickable items (eg. '.gs-dist .chip')
//   getFilter : (clickedEl) => { key, value } -- the filter payload
//   activeClass: optional CSS class to toggle as the active filter
function attachClickToFilter({ root = document, selector, getFilter, activeClass = 'is-active' }) {
  root.querySelectorAll(selector).forEach(el => {
    el.style.cursor = 'pointer';
    el.addEventListener('click', () => {
      const payload = getFilter(el);
      if (!payload) return;
      // Toggle active state: clicking the active filter clears it
      const wasActive = el.classList.contains(activeClass);
      root.querySelectorAll(`${selector}.${activeClass}`).forEach(other => {
        other.classList.remove(activeClass);
      });
      if (!wasActive) el.classList.add(activeClass);
      dispatchFilter(wasActive ? null : payload);
    });
  });
}

function dispatchFilter(payload) {
  document.dispatchEvent(new CustomEvent('chart-filter', { detail: payload }));
}

// Convenience listener registration. Callers pass a callback that receives
// the filter payload (or null when the filter is cleared) and decides what
// to do with the list below the chart.
function onFilterChange(callback) {
  document.addEventListener('chart-filter', ev => callback(ev.detail));
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    attachChartHover,
    attachClickToFilter,
    dispatchFilter,
    onFilterChange,
  };
}
