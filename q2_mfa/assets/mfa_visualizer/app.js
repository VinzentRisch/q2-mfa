const COLOR_PALETTES = {
  Plotly: {
    kind: 'categorical',
    colors: ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880'],
  },
  Safe: {
    kind: 'categorical',
    colors: ['#1F77B4', '#FF7F0E', '#2CA02C', '#D62728', '#9467BD', '#8C564B', '#E377C2', '#7F7F7F'],
  },
  Earth: {
    kind: 'categorical',
    colors: ['#264653', '#2A9D8F', '#E9C46A', '#F4A261', '#E76F51', '#8AB17D', '#577590', '#BC6C25'],
  },
  Viridis: {
    kind: 'numeric',
    scale: 'Viridis',
    colors: ['#440154', '#3B528B', '#21918C', '#5DC863', '#FDE725'],
  },
  Cividis: {
    kind: 'numeric',
    scale: 'Cividis',
    colors: ['#00224E', '#434E6C', '#7D7C78', '#BCA76C', '#FFE945'],
  },
  Plasma: {
    kind: 'numeric',
    scale: 'Plasma',
    colors: ['#0D0887', '#7E03A8', '#CC4778', '#F89540', '#F0F921'],
  },
  Blues: {
    kind: 'numeric',
    scale: 'Blues',
    colors: ['#EFF3FF', '#BDD7E7', '#6BAED6', '#3182BD', '#08519C'],
  },
  RdBu: {
    kind: 'numeric',
    scale: 'RdBu',
    colors: ['#67001F', '#D6604D', '#F7F7F7', '#4393C3', '#053061'],
  },
};

const MISSING_VALUE_TOKEN = '__MISSING__';
const DEFAULT_MARKER_COLOR = '#126782';
const ELLIPSE_SCALE = 2.4477;

const payload = window.MFA_VISUALIZER_DATA;
const metadataByName = Object.fromEntries(
  payload.metadata_columns.map((column) => [column.name, column])
);
const dimensionsByKey = Object.fromEntries(
  payload.dimensions.map((dimension) => [dimension.key, dimension])
);

const state = {
  xDimension: payload.default_x,
  yDimension: payload.default_y,
  colorBy: '',
  colorPalette: 'Plotly',
  showBarycenter: false,
  filterBy: '',
  categoricalFilterValues: new Set(),
  numericFilterMin: null,
  numericFilterMax: null,
  darkMode: true,
};

function initialize() {
  document.getElementById('visualizer-title').textContent = payload.title;
  populateDimensionSelectors();
  populateColorControls();
  populateFilterSelector();
  applyTheme();
  bindEvents();
  renderFilterControls();
  renderPlot();
}

function populateDimensionSelectors() {
  const xDimension = document.getElementById('x-dimension');
  const yDimension = document.getElementById('y-dimension');

  payload.dimensions.forEach((dimension) => {
    const xOption = new Option(dimension.label, dimension.key);
    const yOption = new Option(dimension.label, dimension.key);
    xDimension.add(xOption);
    yDimension.add(yOption);
  });

  xDimension.value = state.xDimension;
  yDimension.value = state.yDimension;
}

function populateColorControls() {
  const colorBy = document.getElementById('color-by');
  colorBy.add(new Option('None', ''));
  payload.metadata_columns.forEach((column) => {
    colorBy.add(new Option(column.name, column.name));
  });

  repopulateColorPaletteOptions();
  document.getElementById('show-barycenter').checked = state.showBarycenter;
}

function populateFilterSelector() {
  const filterBy = document.getElementById('filter-by');
  filterBy.add(new Option('None', ''));
  payload.metadata_columns.forEach((column) => {
    filterBy.add(new Option(column.name, column.name));
  });
}

function bindEvents() {
  document.getElementById('x-dimension').addEventListener('change', (event) => {
    state.xDimension = event.target.value;
    renderPlot();
  });

  document.getElementById('y-dimension').addEventListener('change', (event) => {
    state.yDimension = event.target.value;
    renderPlot();
  });

  document.getElementById('color-by').addEventListener('change', (event) => {
    state.colorBy = event.target.value;
    repopulateColorPaletteOptions();
    renderPlot();
  });

  document.getElementById('color-palette').addEventListener('change', (event) => {
    state.colorPalette = event.target.value;
    renderPlot();
  });

  document.getElementById('show-barycenter').addEventListener('change', (event) => {
    state.showBarycenter = event.target.checked;
    renderPlot();
  });

  document.getElementById('filter-by').addEventListener('change', (event) => {
    state.filterBy = event.target.value;
    resetFilterState();
    renderFilterControls();
    renderPlot();
  });

  document.getElementById('dark-mode-toggle').addEventListener('change', (event) => {
    state.darkMode = event.target.checked;
    applyTheme();
    renderPlot();
  });
}

function applyTheme() {
  document.body.classList.toggle('dark-mode', state.darkMode);
  document.getElementById('dark-mode-toggle').checked = state.darkMode;
}

function resetFilterState() {
  state.categoricalFilterValues = new Set();
  state.numericFilterMin = null;
  state.numericFilterMax = null;
}

function renderFilterControls() {
  const container = document.getElementById('filter-controls');
  container.innerHTML = '';

  if (!state.filterBy) {
    container.innerHTML = '<span class="filter-placeholder">No metadata filter applied.</span>';
    document.getElementById('filter-summary').textContent = 'Showing all samples';
    return;
  }

  const column = metadataByName[state.filterBy];
  if (column.type === 'categorical') {
    renderCategoricalFilterControls(container, column);
    return;
  }

  renderNumericFilterControls(container, column);
}

function renderCategoricalFilterControls(container, column) {
  if (!state.categoricalFilterValues.size) {
    column.values.forEach((value) => state.categoricalFilterValues.add(value));
    if (column.has_missing) {
      state.categoricalFilterValues.add(MISSING_VALUE_TOKEN);
    }
  }

  const heading = document.createElement('div');
  heading.className = 'filter-heading';
  heading.textContent = `Include values from ${column.name}`;
  container.appendChild(heading);

  const options = document.createElement('div');
  options.className = 'filter-options';

  column.values.forEach((value) => {
    options.appendChild(
      buildCategoricalFilterOption(value, value, state.categoricalFilterValues.has(value))
    );
  });

  if (column.has_missing) {
    options.appendChild(
      buildCategoricalFilterOption(
        MISSING_VALUE_TOKEN,
        'Missing',
        state.categoricalFilterValues.has(MISSING_VALUE_TOKEN)
      )
    );
  }

  container.appendChild(options);
}

function buildCategoricalFilterOption(value, label, checked) {
  const wrapper = document.createElement('label');
  wrapper.className = 'filter-option';

  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.checked = checked;
  checkbox.value = value;
  checkbox.addEventListener('change', (event) => {
    if (event.target.checked) {
      state.categoricalFilterValues.add(value);
    } else {
      state.categoricalFilterValues.delete(value);
    }
    renderPlot();
  });

  const text = document.createElement('span');
  text.textContent = label;

  wrapper.appendChild(checkbox);
  wrapper.appendChild(text);
  return wrapper;
}

function renderNumericFilterControls(container, column) {
  if (state.numericFilterMin === null) {
    state.numericFilterMin = column.min;
    state.numericFilterMax = column.max;
  }

  const heading = document.createElement('div');
  heading.className = 'filter-heading';
  heading.textContent = `Range filter for ${column.name}`;
  container.appendChild(heading);

  const grid = document.createElement('div');
  grid.className = 'numeric-filter-grid';
  grid.appendChild(
    buildNumericFilterInput('Minimum', state.numericFilterMin, (value) => {
      state.numericFilterMin = value;
      renderPlot();
    })
  );
  grid.appendChild(
    buildNumericFilterInput('Maximum', state.numericFilterMax, (value) => {
      state.numericFilterMax = value;
      renderPlot();
    })
  );

  container.appendChild(grid);
}

function buildNumericFilterInput(label, value, onInput) {
  const wrapper = document.createElement('label');
  wrapper.className = 'control-group';
  wrapper.textContent = label;

  const input = document.createElement('input');
  input.type = 'number';
  input.step = 'any';
  input.value = value;
  input.addEventListener('input', (event) => {
    const nextValue = event.target.value === '' ? null : Number(event.target.value);
    onInput(nextValue);
  });

  wrapper.appendChild(input);
  return wrapper;
}

function getFilteredSamples() {
  if (!state.filterBy) {
    return payload.samples;
  }

  const column = metadataByName[state.filterBy];
  if (column.type === 'categorical') {
    return payload.samples.filter((sample) => {
      const value = sample.metadata[state.filterBy];
      const normalizedValue = value === null ? MISSING_VALUE_TOKEN : value;
      return state.categoricalFilterValues.has(normalizedValue);
    });
  }

  return payload.samples.filter((sample) => {
    const value = sample.metadata[state.filterBy];
    if (value === null) {
      return false;
    }

    const lowerBound = state.numericFilterMin ?? column.min;
    const upperBound = state.numericFilterMax ?? column.max;
    return value >= lowerBound && value <= upperBound;
  });
}

function renderPlot() {
  const filteredSamples = getFilteredSamples();
  const traces = buildTraces(filteredSamples);
  const layout = buildLayout(filteredSamples.length === 0);

  Plotly.react('sample-plot', traces, layout, {
    responsive: true,
    displaylogo: false,
    scrollZoom: true,
    toImageButtonOptions: {
      format: 'png',
      filename: buildDownloadFilename('png').replace('.png', ''),
      width: 1400,
      height: 900,
      scale: 2,
    },
    modeBarButtonsToAdd: [
      {
        name: 'Download SVG',
        icon: Plotly.Icons.camera,
        click: () => {
          downloadPlotImage('svg');
        },
      },
    ],
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
  });

  renderVariancePlot();
  updateStatus(filteredSamples);
}

function buildDownloadFilename(extension) {
  const xLabel = state.xDimension.toLowerCase().replace(/\s+/g, '-');
  const yLabel = state.yDimension.toLowerCase().replace(/\s+/g, '-');
  return `mfa-sample-scores-${xLabel}-vs-${yLabel}.${extension}`;
}

function downloadPlotImage(format) {
  Plotly.downloadImage('sample-plot', {
    format,
    filename: buildDownloadFilename(format).replace(`.${format}`, ''),
    width: 1400,
    height: 900,
    scale: 2,
  });
}

function repopulateColorPaletteOptions() {
  const colorPalette = document.getElementById('color-palette');
  const paletteKind = getActivePaletteKind();
  const paletteNames = Object.keys(COLOR_PALETTES).filter(
    (paletteName) => COLOR_PALETTES[paletteName].kind === paletteKind
  );

  colorPalette.innerHTML = '';
  paletteNames.forEach((paletteName) => {
    colorPalette.add(new Option(paletteName, paletteName));
  });

  if (!paletteNames.includes(state.colorPalette)) {
    state.colorPalette = paletteNames[0];
  }

  colorPalette.value = state.colorPalette;
}

function getActivePaletteKind() {
  const colorColumn = metadataByName[state.colorBy];
  return colorColumn?.type === 'numeric' ? 'numeric' : 'categorical';
}

function buildTraces(samples) {
  const colorColumn = metadataByName[state.colorBy];
  if (!colorColumn) {
    const traces = [buildSingleTrace(samples, DEFAULT_MARKER_COLOR, 'Samples')];
    return appendBarycenterTraces(traces, samples, colorColumn);
  }

  if (colorColumn.type === 'numeric') {
    return appendBarycenterTraces(buildNumericTraces(samples, colorColumn), samples, colorColumn);
  }

  return appendBarycenterTraces(buildCategoricalTraces(samples, colorColumn), samples, colorColumn);
}

function buildSingleTrace(samples, color, name) {
  return {
    type: 'scattergl',
    mode: 'markers',
    name,
    x: samples.map((sample) => sample.coords[state.xDimension]),
    y: samples.map((sample) => sample.coords[state.yDimension]),
    text: samples.map(buildHoverText),
    hovertemplate: '%{text}<extra></extra>',
    marker: {
      color,
      size: 11,
      opacity: 0.9,
      line: { color: getThemeColors().markerLine, width: 1 },
    },
  };
}

function buildNumericTraces(samples, colorColumn) {
  const themeColors = getThemeColors();
  const numericSamples = samples.filter(
    (sample) => sample.metadata[colorColumn.name] !== null
  );
  const missingSamples = samples.filter(
    (sample) => sample.metadata[colorColumn.name] === null
  );

  const traces = [];
  if (numericSamples.length) {
    traces.push({
      type: 'scattergl',
      mode: 'markers',
      name: colorColumn.name,
      x: numericSamples.map((sample) => sample.coords[state.xDimension]),
      y: numericSamples.map((sample) => sample.coords[state.yDimension]),
      text: numericSamples.map(buildHoverText),
      hovertemplate: '%{text}<extra></extra>',
      marker: {
        color: numericSamples.map((sample) => sample.metadata[colorColumn.name]),
        colorscale: getNumericColorscale(state.colorPalette),
        colorbar: {
          title: {
            text: colorColumn.name,
            font: { color: themeColors.font },
          },
          thickness: 18,
          tickfont: { color: themeColors.font },
        },
        size: 11,
        opacity: 0.9,
        line: { color: themeColors.markerLine, width: 1 },
        cmin: colorColumn.min,
        cmax: colorColumn.max,
      },
    });
  }

  if (missingSamples.length) {
    traces.push(buildSingleTrace(missingSamples, '#94A3B8', 'Missing'));
  }

  return traces;
}

function buildCategoricalTraces(samples, colorColumn) {
  const palette = getCategoricalColors(colorColumn.values.length + Number(colorColumn.has_missing));
  const orderedCategories = [...colorColumn.values];
  if (colorColumn.has_missing) {
    orderedCategories.push(MISSING_VALUE_TOKEN);
  }

  return orderedCategories
    .map((category, index) => {
      const subset = samples.filter((sample) => {
        const value = sample.metadata[colorColumn.name];
        return category === MISSING_VALUE_TOKEN ? value === null : value === category;
      });

      if (!subset.length) {
        return null;
      }

      const label = category === MISSING_VALUE_TOKEN ? 'Missing' : category;
      return buildSingleTrace(subset, palette[index % palette.length], label);
    })
    .filter(Boolean);
}

function appendBarycenterTraces(traces, samples, colorColumn) {
  if (!state.showBarycenter) {
    return traces;
  }

  if (colorColumn?.type === 'categorical') {
    const orderedCategories = [...colorColumn.values];
    if (colorColumn.has_missing) {
      orderedCategories.push(MISSING_VALUE_TOKEN);
    }

    const palette = getCategoricalColors(orderedCategories.length);
    orderedCategories.forEach((category, index) => {
      const subset = samples.filter((sample) => {
        const value = sample.metadata[colorColumn.name];
        return category === MISSING_VALUE_TOKEN ? value === null : value === category;
      });

      const label = category === MISSING_VALUE_TOKEN ? 'Missing' : category;
      const ellipseTrace = buildBarycenterEllipseTrace(subset, palette[index], label);
      if (ellipseTrace) {
        traces.push(ellipseTrace);
      }
    });
    return traces;
  }

  const ellipseColor = colorColumn?.type === 'numeric'
    ? getCategoricalColors(1)[0]
    : DEFAULT_MARKER_COLOR;
  const ellipseTrace = buildBarycenterEllipseTrace(samples, ellipseColor, 'Visible samples');
  if (ellipseTrace) {
    traces.push(ellipseTrace);
  }
  return traces;
}

function buildBarycenterEllipseTrace(samples, color, label) {
  const ellipsePoints = computeEllipsePoints(samples);
  if (!ellipsePoints) {
    return null;
  }

  return {
    type: 'scatter',
    mode: 'lines',
    name: `${label} barycenter`,
    x: ellipsePoints.x,
    y: ellipsePoints.y,
    line: {
      color,
      width: 2,
    },
    fill: 'toself',
    fillcolor: withAlpha(color, 0.14),
    hoverinfo: 'skip',
    showlegend: false,
  };
}

function computeEllipsePoints(samples) {
  if (samples.length < 2) {
    return null;
  }

  const points = samples.map((sample) => [
    sample.coords[state.xDimension],
    sample.coords[state.yDimension],
  ]);
  const meanX = average(points.map((point) => point[0]));
  const meanY = average(points.map((point) => point[1]));

  let covXX = 0;
  let covXY = 0;
  let covYY = 0;
  points.forEach(([x, y]) => {
    const dx = x - meanX;
    const dy = y - meanY;
    covXX += dx * dx;
    covXY += dx * dy;
    covYY += dy * dy;
  });

  const divisor = Math.max(points.length - 1, 1);
  covXX /= divisor;
  covXY /= divisor;
  covYY /= divisor;

  const trace = covXX + covYY;
  const determinant = covXX * covYY - covXY * covXY;
  const delta = Math.max(trace * trace / 4 - determinant, 0);
  const lambda1 = trace / 2 + Math.sqrt(delta);
  const lambda2 = Math.max(trace / 2 - Math.sqrt(delta), 0);

  if (lambda1 <= 0 && lambda2 <= 0) {
    return null;
  }

  let vectorX = 1;
  let vectorY = 0;
  if (Math.abs(covXY) > 1e-10 || Math.abs(lambda1 - covXX) > 1e-10) {
    vectorX = covXY;
    vectorY = lambda1 - covXX;
    const magnitude = Math.hypot(vectorX, vectorY) || 1;
    vectorX /= magnitude;
    vectorY /= magnitude;
  }

  const orthogonalX = -vectorY;
  const orthogonalY = vectorX;
  const radius1 = ELLIPSE_SCALE * Math.sqrt(Math.max(lambda1, 0));
  const radius2 = ELLIPSE_SCALE * Math.sqrt(Math.max(lambda2, 0));

  const x = [];
  const y = [];
  for (let step = 0; step <= 60; step += 1) {
    const theta = (step / 60) * Math.PI * 2;
    const ellipseX =
      meanX +
      radius1 * Math.cos(theta) * vectorX +
      radius2 * Math.sin(theta) * orthogonalX;
    const ellipseY =
      meanY +
      radius1 * Math.cos(theta) * vectorY +
      radius2 * Math.sin(theta) * orthogonalY;
    x.push(ellipseX);
    y.push(ellipseY);
  }

  return { x, y };
}

function average(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function getCategoricalColors(count) {
  const palette = COLOR_PALETTES[state.colorPalette] ?? COLOR_PALETTES.Plotly;
  const colors = palette.colors;
  return Array.from({ length: count }, (_, index) => colors[index % colors.length]);
}

function getNumericColorscale(paletteName) {
  const palette = COLOR_PALETTES[paletteName] ?? COLOR_PALETTES.Viridis;
  if (palette.scale) {
    return palette.scale;
  }

  return palette.colors.map((color, index) => [
    index / Math.max(palette.colors.length - 1, 1),
    color,
  ]);
}

function withAlpha(hexColor, alpha) {
  const hex = hexColor.replace('#', '');
  const normalized = hex.length === 3
    ? hex.split('').map((char) => char + char).join('')
    : hex;
  const red = parseInt(normalized.slice(0, 2), 16);
  const green = parseInt(normalized.slice(2, 4), 16);
  const blue = parseInt(normalized.slice(4, 6), 16);
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function buildLayout(isEmpty) {
  const themeColors = getThemeColors();
  return {
    paper_bgcolor: 'rgba(0, 0, 0, 0)',
    plot_bgcolor: 'rgba(255, 255, 255, 0)',
    dragmode: 'zoom',
    hovermode: 'closest',
    margin: { t: 20, r: 20, b: 70, l: 80 },
    font: {
      color: themeColors.font,
      family: '"IBM Plex Sans", "Helvetica Neue", sans-serif',
    },
    legend: {
      orientation: 'h',
      yanchor: 'bottom',
      y: 1.02,
      xanchor: 'left',
      x: 0,
      font: { color: themeColors.font },
    },
    xaxis: {
      title: {
        text: dimensionsByKey[state.xDimension].axis_title,
        font: { color: themeColors.font },
      },
      zeroline: true,
      zerolinecolor: themeColors.zeroline,
      zerolinewidth: 1,
      gridcolor: themeColors.grid,
      gridwidth: 1,
      tickfont: { color: themeColors.font },
    },
    yaxis: {
      title: {
        text: dimensionsByKey[state.yDimension].axis_title,
        font: { color: themeColors.font },
      },
      zeroline: true,
      zerolinecolor: themeColors.zeroline,
      zerolinewidth: 1,
      gridcolor: themeColors.grid,
      gridwidth: 1,
      tickfont: { color: themeColors.font },
    },
    annotations: isEmpty
      ? [
          {
            text: 'No samples match the active filter.',
            showarrow: false,
            xref: 'paper',
            yref: 'paper',
            x: 0.5,
            y: 0.5,
            font: { size: 16, color: themeColors.annotation },
          },
        ]
      : [],
  };
}

function renderVariancePlot() {
  const components = payload.component_variance.filter(
    (component) => component.variance_explained !== null
  );
  const selectedDimensions = new Set([state.xDimension, state.yDimension]);
  const themeColors = getThemeColors();
  const hasVariance = components.length > 0;

  const trace = {
    type: 'bar',
    x: components.map((component) => component.label),
    y: components.map((component) => component.variance_explained * 100),
    marker: {
      color: components.map((component) =>
        selectedDimensions.has(component.key) ? '#C95E37' : DEFAULT_MARKER_COLOR
      ),
      line: {
        color: themeColors.markerLine,
        width: 1,
      },
    },
    customdata: components.map((component) => [component.variance_explained * 100]),
    hovertemplate: '%{x}: %{customdata[0]:.2f}% explained<extra></extra>',
  };

  Plotly.react(
    'variance-plot',
    hasVariance ? [trace] : [],
    buildVarianceLayout(hasVariance),
    {
      responsive: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['lasso2d', 'select2d', 'zoom2d', 'pan2d'],
    }
  );

  updateVarianceSummary(components);
}

function buildVarianceLayout(hasVariance) {
  const themeColors = getThemeColors();
  return {
    paper_bgcolor: 'rgba(0, 0, 0, 0)',
    plot_bgcolor: 'rgba(255, 255, 255, 0)',
    margin: { t: 20, r: 20, b: 60, l: 80 },
    font: {
      color: themeColors.font,
      family: '"IBM Plex Sans", "Helvetica Neue", sans-serif',
    },
    bargap: 0.24,
    xaxis: {
      title: {
        text: 'Component',
        font: { color: themeColors.font },
      },
      tickfont: { color: themeColors.font },
    },
    yaxis: {
      title: {
        text: 'Explained variance (%)',
        font: { color: themeColors.font },
      },
      rangemode: 'tozero',
      gridcolor: themeColors.grid,
      gridwidth: 1,
      tickfont: { color: themeColors.font },
    },
    annotations: hasVariance
      ? []
      : [
          {
            text: 'Explained variance values are not available.',
            showarrow: false,
            xref: 'paper',
            yref: 'paper',
            x: 0.5,
            y: 0.5,
            font: { size: 16, color: themeColors.annotation },
          },
        ],
  };
}

function getThemeColors() {
  const styles = getComputedStyle(document.body);
  return {
    font: styles.getPropertyValue('--plot-font').trim(),
    grid: styles.getPropertyValue('--plot-grid').trim(),
    zeroline: styles.getPropertyValue('--plot-zero').trim(),
    annotation: styles.getPropertyValue('--plot-annotation').trim(),
    markerLine: styles.getPropertyValue('--plot-marker-line').trim(),
  };
}

function buildHoverText(sample) {
  const lines = [
    `<b>${sample.sample_id}</b>`,
    `${dimensionsByKey[state.xDimension].label}: ${formatValue(sample.coords[state.xDimension])}`,
    `${dimensionsByKey[state.yDimension].label}: ${formatValue(sample.coords[state.yDimension])}`,
  ];

  payload.metadata_columns.forEach((column) => {
    lines.push(`${column.name}: ${formatMetadataValue(sample.metadata[column.name])}`);
  });

  return lines.join('<br>');
}

function updateStatus(filteredSamples) {
  document.getElementById('sample-count').textContent =
    `${filteredSamples.length} of ${payload.samples.length} samples shown`;

  if (!state.filterBy) {
    document.getElementById('filter-summary').textContent = 'Showing all samples';
    return;
  }

  const column = metadataByName[state.filterBy];
  if (column.type === 'categorical') {
    const selectedValues = column.values.filter((value) =>
      state.categoricalFilterValues.has(value)
    );
    if (column.has_missing && state.categoricalFilterValues.has(MISSING_VALUE_TOKEN)) {
      selectedValues.push('Missing');
    }
    document.getElementById('filter-summary').textContent =
      `Filter: ${state.filterBy} in ${selectedValues.join(', ') || 'none'}`;
    return;
  }

  const lowerBound = state.numericFilterMin ?? column.min;
  const upperBound = state.numericFilterMax ?? column.max;
  document.getElementById('filter-summary').textContent =
    `Filter: ${state.filterBy} from ${formatValue(lowerBound)} to ${formatValue(upperBound)}`;
}

function updateVarianceSummary(components) {
  const totalExplained = components.reduce(
    (sum, component) => sum + component.variance_explained,
    0
  );
  document.getElementById('variance-summary').textContent = components.length
    ? `${formatValue(totalExplained * 100)}% across ${components.length} components`
    : 'Variance unavailable';
}

function formatMetadataValue(value) {
  return value === null ? 'Missing' : formatValue(value);
}

function formatValue(value) {
  if (typeof value === 'number') {
    return Number.isInteger(value) ? String(value) : value.toFixed(3).replace(/\.?0+$/, '');
  }

  return String(value);
}

initialize();
