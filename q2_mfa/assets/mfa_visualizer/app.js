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
const SELECTED_DIMENSION_COLOR = '#083D5B';
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
  showPartialOverlay: false,
  showFeatureCorrelations: false,
  topFeatureCount: 10,
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
  document.getElementById('show-partial-overlay').checked = state.showPartialOverlay;
  document.getElementById('show-feature-correlations').checked = state.showFeatureCorrelations;
  document.getElementById('top-feature-count').value = state.topFeatureCount;
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

  document.getElementById('show-partial-overlay').addEventListener('change', (event) => {
    state.showPartialOverlay = event.target.checked;
    renderPlot();
  });

  document.getElementById('show-feature-correlations').addEventListener('change', (event) => {
    state.showFeatureCorrelations = event.target.checked;
    renderPlot();
  });

  document.getElementById('top-feature-count').addEventListener('input', (event) => {
    const nextValue = Number(event.target.value);
    if (!Number.isFinite(nextValue) || nextValue < 1) {
      return;
    }
    state.topFeatureCount = Math.floor(nextValue);
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
          downloadPlotImage('sample-plot', buildDownloadFilename('svg'), 'svg');
        },
      },
    ],
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
  });

  renderGroupPlot();
  renderPartialAxesPlot();
  renderVariancePlot();
  updateStatus(filteredSamples);
}

function buildDownloadFilename(extension) {
  const xLabel = state.xDimension.toLowerCase().replace(/\s+/g, '-');
  const yLabel = state.yDimension.toLowerCase().replace(/\s+/g, '-');
  return `mfa-sample-scores-${xLabel}-vs-${yLabel}.${extension}`;
}

function downloadPlotImage(plotId, filename, format) {
  Plotly.downloadImage(plotId, {
    format,
    filename: filename.replace(`.${format}`, ''),
    width: 1400,
    height: 900,
    scale: 2,
  });
}

function buildVarianceDownloadFilename(extension) {
  return `mfa-explained-variance-by-component.${extension}`;
}

function buildCumulativeVarianceDownloadFilename(extension) {
  return `mfa-cumulative-explained-variance.${extension}`;
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
  const partialOverlayTraces = buildPartialOverlayTraces(samples, colorColumn);
  const featureCorrelationTraces = buildFeatureCorrelationTraces();

  if (!colorColumn) {
    const traces = [
      buildSingleTrace(samples, DEFAULT_MARKER_COLOR, 'Samples'),
      ...partialOverlayTraces,
      ...featureCorrelationTraces,
    ];
    return appendBarycenterTraces(traces, samples, colorColumn);
  }

  if (colorColumn.type === 'numeric') {
    return appendBarycenterTraces(
      [...buildNumericTraces(samples, colorColumn), ...partialOverlayTraces, ...featureCorrelationTraces],
      samples,
      colorColumn
    );
  }

  return appendBarycenterTraces(
    [...buildCategoricalTraces(samples, colorColumn), ...partialOverlayTraces, ...featureCorrelationTraces],
    samples,
    colorColumn
  );
}

function buildFeatureCorrelationTraces() {
  if (!state.showFeatureCorrelations || !payload.feature_correlations?.length) {
    return [];
  }

  const visibleFeatures = payload.feature_correlations
    .map((feature) => ({
      ...feature,
      x: feature.coords[state.xDimension],
      y: feature.coords[state.yDimension],
    }))
    .filter((feature) => feature.x !== null && feature.y !== null);

  if (!visibleFeatures.length) {
    return [];
  }

  // Rank by correlation magnitude in the currently displayed 2D plane so the
  // overlay surfaces the variables best represented in the exact view the user
  // is inspecting, rather than overemphasizing features strong on only one axis.
  const rankedFeatures = visibleFeatures
    .map((feature) => ({
      ...feature,
      rankingScore: Math.hypot(feature.x, feature.y),
    }))
    .sort((a, b) => b.rankingScore - a.rankingScore)
    .slice(0, state.topFeatureCount);

  if (!rankedFeatures.length) {
    return [];
  }

  const groupOrder = [...new Set(rankedFeatures.map((feature) => feature.group))].sort();
  const groupColors = Object.fromEntries(
    groupOrder.map((group, index) => [group, COLOR_PALETTES.Earth.colors[index % COLOR_PALETTES.Earth.colors.length]])
  );

  const traces = [];
  groupOrder.forEach((group) => {
    const groupFeatures = rankedFeatures.filter((feature) => feature.group === group);
    if (!groupFeatures.length) {
      return;
    }

    const lineX = [];
    const lineY = [];
    groupFeatures.forEach((feature) => {
      lineX.push(0, feature.x, null);
      lineY.push(0, feature.y, null);
    });

    traces.push({
      type: 'scatter',
      mode: 'lines',
      name: `${group} feature vectors`,
      legendgroup: `feature-correlations:${group}`,
      x: lineX,
      y: lineY,
      line: {
        color: withAlpha(groupColors[group], 0.65),
        width: 1.5,
      },
      hoverinfo: 'skip',
      showlegend: false,
    });

    traces.push({
      type: 'scattergl',
      mode: 'markers+text',
      name: group,
      legendgroup: `feature-correlations:${group}`,
      showlegend: true,
      x: groupFeatures.map((feature) => feature.x),
      y: groupFeatures.map((feature) => feature.y),
      text: groupFeatures.map((feature) => feature.feature_name),
      textposition: 'top center',
      textfont: {
        color: getThemeColors().font,
        size: 11,
      },
      texttemplate: '%{text}',
      hovertemplate:
        '<b>%{customdata[0]}</b><br>' +
        'Group: %{customdata[1]}<br>' +
        `${state.xDimension}: %{x:.3f}<br>` +
        `${state.yDimension}: %{y:.3f}<br>` +
        'Plane magnitude: %{customdata[2]:.3f}<extra></extra>',
      customdata: groupFeatures.map((feature) => [
        feature.feature_id,
        feature.group,
        feature.rankingScore,
      ]),
      marker: {
        color: groupColors[group],
        size: 9,
        opacity: 0.95,
        symbol: 'circle-open',
        line: {
          color: groupColors[group],
          width: 2,
        },
      },
    });
  });

  return traces;
}

function buildPartialOverlayTraces(samples, colorColumn) {
  if (
    !state.showPartialOverlay ||
    !payload.partial_samples?.length ||
    !payload.partial_groups?.length
  ) {
    return [];
  }

  const visibleSampleIds = new Set(samples.map((sample) => sample.sample_id));
  const visibleSamplesById = Object.fromEntries(
    samples.map((sample) => [sample.sample_id, sample])
  );
  const visiblePartialSamples = payload.partial_samples.filter(
    (entry) =>
      visibleSampleIds.has(entry.sample_id) &&
      entry.coords[state.xDimension] !== undefined &&
      entry.coords[state.yDimension] !== undefined
  );

  if (!visiblePartialSamples.length) {
    return [];
  }

  const palette = COLOR_PALETTES.Earth.colors;
  const traces = [];

  if (colorColumn?.type === 'categorical') {
    const orderedCategories = [...colorColumn.values];
    if (colorColumn.has_missing) {
      orderedCategories.push(MISSING_VALUE_TOKEN);
    }
    const partialLegendGroupsShown = new Set();

    orderedCategories.forEach((category) => {
      const categorySamples = samples.filter((sample) => {
        const value = sample.metadata[colorColumn.name];
        return category === MISSING_VALUE_TOKEN ? value === null : value === category;
      });
      if (!categorySamples.length) {
        return;
      }

      const categorySampleIds = new Set(categorySamples.map((sample) => sample.sample_id));
      payload.partial_groups.forEach((group, index) => {
        const groupEntries = visiblePartialSamples.filter(
          (entry) => entry.group === group && categorySampleIds.has(entry.sample_id)
        );
        if (!groupEntries.length) {
          return;
        }

        const color = palette[index % palette.length];
        const partialLegendGroup = `partial:${group}`;
        const showPartialLegend = !partialLegendGroupsShown.has(group);
        partialLegendGroupsShown.add(group);
        traces.push(
          buildPartialConnectorTrace(
            groupEntries,
            visibleSamplesById,
            color,
            group,
            partialLegendGroup
          )
        );
        traces.push(
          buildPartialPointTrace(
            groupEntries,
            color,
            group,
            partialLegendGroup,
            showPartialLegend
          )
        );
      });
    });

    return traces;
  }

  payload.partial_groups.forEach((group, index) => {
    const groupEntries = visiblePartialSamples.filter((entry) => entry.group === group);
    if (!groupEntries.length) {
      return;
    }

    const color = palette[index % palette.length];
    traces.push(
      buildPartialConnectorTrace(
        groupEntries,
        visibleSamplesById,
        color,
        group,
        `partial:${group}`
      )
    );
    traces.push(
      buildPartialPointTrace(groupEntries, color, group, `partial:${group}`, true)
    );
  });

  return traces;
}

function buildPartialConnectorTrace(
  groupEntries,
  visibleSamplesById,
  color,
  group,
  legendgroup
) {
  const x = [];
  const y = [];

  groupEntries.forEach((entry) => {
    const sample = visibleSamplesById[entry.sample_id];
    x.push(sample.coords[state.xDimension], entry.coords[state.xDimension], null);
    y.push(sample.coords[state.yDimension], entry.coords[state.yDimension], null);
  });

  return {
    type: 'scattergl',
    mode: 'lines',
    name: `${group} connectors`,
    legendgroup,
    x,
    y,
    line: {
      color: withAlpha(color, 0.4),
      width: 1.5,
    },
    hoverinfo: 'skip',
    showlegend: false,
  };
}

function buildPartialPointTrace(groupEntries, color, group, legendgroup, showlegend) {
  return {
    type: 'scattergl',
    mode: 'markers',
    name: `${group} partial`,
    legendgroup,
    showlegend,
    x: groupEntries.map((entry) => entry.coords[state.xDimension]),
    y: groupEntries.map((entry) => entry.coords[state.yDimension]),
    text: groupEntries.map(buildPartialHoverText),
    hovertemplate: '%{text}<extra></extra>',
    marker: {
      color,
      size: 8,
      opacity: 0.9,
      symbol: 'diamond-open',
      line: { color, width: 2 },
    },
  };
}

function buildSingleTrace(samples, color, name, options = {}) {
  return {
    type: 'scatter',
    mode: 'markers',
    name,
    legendgroup: options.legendgroup,
    showlegend: options.showlegend ?? true,
    x: samples.map((sample) => sample.coords[state.xDimension]),
    y: samples.map((sample) => sample.coords[state.yDimension]),
    customdata: samples.map(buildHoverText),
    hovertemplate: '%{customdata}<extra></extra>',
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
      type: 'scatter',
      mode: 'markers',
      name: colorColumn.name,
      x: numericSamples.map((sample) => sample.coords[state.xDimension]),
      y: numericSamples.map((sample) => sample.coords[state.yDimension]),
      customdata: numericSamples.map(buildHoverText),
      hovertemplate: '%{customdata}<extra></extra>',
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
      return buildSingleTrace(subset, palette[index % palette.length], label, {
        legendgroup: `metadata:${label}`,
      });
    })
    .filter(Boolean);
}

function appendBarycenterTraces(traces, samples, colorColumn) {
  if (!state.showBarycenter) {
    return traces;
  }

  const ellipseTraces = [];

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
      const ellipseTrace = buildBarycenterEllipseTrace(
        subset,
        palette[index],
        label,
        `metadata:${label}`
      );
      if (ellipseTrace) {
        ellipseTraces.push(ellipseTrace);
      }
    });
    return [...ellipseTraces, ...traces];
  }

  const ellipseColor = colorColumn?.type === 'numeric'
    ? getCategoricalColors(1)[0]
    : DEFAULT_MARKER_COLOR;
  const ellipseTrace = buildBarycenterEllipseTrace(
    samples,
    ellipseColor,
    'Visible samples',
    'visible-samples'
  );
  if (ellipseTrace) {
    ellipseTraces.push(ellipseTrace);
  }
  return [...ellipseTraces, ...traces];
}

function buildBarycenterEllipseTrace(samples, color, label, legendgroup) {
  const ellipsePoints = computeEllipsePoints(samples);
  if (!ellipsePoints) {
    return null;
  }

  return {
    type: 'scatter',
    mode: 'lines',
    name: `${label} barycenter`,
    legendgroup,
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
    margin: { t: 104, r: 40, b: 70, l: 80 },
    font: {
      color: themeColors.font,
      family: '"IBM Plex Sans", "Helvetica Neue", sans-serif',
    },
    legend: {
      orientation: 'h',
      groupclick: 'togglegroup',
      yanchor: 'bottom',
      y: 1.14,
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

function renderGroupPlot() {
  const themeColors = getThemeColors();
  const groups = (payload.group_summary ?? []).filter(
    (entry) =>
      entry.coords[state.xDimension] !== undefined &&
      entry.coords[state.yDimension] !== undefined
  );
  const hasGroups = groups.length > 0;

  const trace = {
    type: 'scatter',
    mode: 'markers+text',
    name: 'Groups',
    x: groups.map((entry) => entry.coords[state.xDimension]),
    y: groups.map((entry) => entry.coords[state.yDimension]),
    text: groups.map((entry) => entry.group),
    textposition: groups.map((entry) =>
      entry.coords[state.xDimension] >= 0 ? 'middle left' : 'middle right'
    ),
    cliponaxis: false,
    textfont: {
      color: themeColors.font,
      family: '"IBM Plex Sans", "Helvetica Neue", sans-serif',
      size: 12,
    },
    hovertemplate: '%{text}<br>%{customdata}<extra></extra>',
    customdata: groups.map(buildGroupHoverText),
    marker: {
      color: groups.map(
        (_, index) => COLOR_PALETTES.Earth.colors[index % COLOR_PALETTES.Earth.colors.length]
      ),
      size: 14,
      symbol: 'diamond',
      line: {
        color: themeColors.markerLine,
        width: 1.5,
      },
    },
  };

  Plotly.react(
    'group-plot',
    hasGroups ? [trace] : [],
    buildGroupLayout(hasGroups),
    {
      responsive: true,
      displaylogo: false,
      toImageButtonOptions: {
        format: 'png',
        filename: 'mfa-group-partial-inertia',
        width: 1200,
        height: 700,
        scale: 2,
      },
      modeBarButtonsToAdd: [
        {
          name: 'Download SVG',
          icon: Plotly.Icons.camera,
          click: () => {
            downloadPlotImage('group-plot', 'mfa-group-partial-inertia.svg', 'svg');
          },
        },
      ],
      modeBarButtonsToRemove: [
        'lasso2d',
        'select2d',
        'zoom2d',
        'pan2d',
        'zoomIn2d',
        'zoomOut2d',
        'autoScale2d',
        'resetScale2d',
      ],
    }
  );

  updateGroupSummary(groups);
}

function buildGroupHoverText(entry) {
  return [
    `${dimensionsByKey[state.xDimension].label} partial inertia: ${formatValue(entry.coords[state.xDimension])}`,
    `${dimensionsByKey[state.yDimension].label} partial inertia: ${formatValue(entry.coords[state.yDimension])}`,
    `${dimensionsByKey[state.xDimension].label} contribution: ${formatValue(entry.contribution[state.xDimension])}`,
    `${dimensionsByKey[state.yDimension].label} contribution: ${formatValue(entry.contribution[state.yDimension])}`,
    `${dimensionsByKey[state.xDimension].label} cos2: ${formatValue(entry.cos2[state.xDimension])}`,
    `${dimensionsByKey[state.yDimension].label} cos2: ${formatValue(entry.cos2[state.yDimension])}`,
    `First eigenvalue: ${formatValue(entry.first_eigenvalue)}`,
    `Weight: ${formatValue(entry.weight)}`,
  ].join('<br>');
}

function buildGroupLayout(hasGroups) {
  const themeColors = getThemeColors();
  return {
    paper_bgcolor: 'rgba(0, 0, 0, 0)',
    plot_bgcolor: 'rgba(255, 255, 255, 0)',
    margin: { t: 20, r: 56, b: 70, l: 90 },
    font: {
      color: themeColors.font,
      family: '"IBM Plex Sans", "Helvetica Neue", sans-serif',
    },
    xaxis: {
      title: {
        text: `${dimensionsByKey[state.xDimension].label} partial inertia`,
        font: { color: themeColors.font },
      },
      rangemode: 'tozero',
      automargin: true,
      zeroline: true,
      zerolinecolor: themeColors.zeroline,
      zerolinewidth: 1,
      gridcolor: themeColors.grid,
      gridwidth: 1,
      tickfont: { color: themeColors.font },
    },
    yaxis: {
      title: {
        text: `${dimensionsByKey[state.yDimension].label} partial inertia`,
        font: { color: themeColors.font },
      },
      rangemode: 'tozero',
      automargin: true,
      zeroline: true,
      zerolinecolor: themeColors.zeroline,
      zerolinewidth: 1,
      gridcolor: themeColors.grid,
      gridwidth: 1,
      tickfont: { color: themeColors.font },
    },
    annotations: hasGroups
      ? []
      : [
          {
            text: 'Group summary values are not available.',
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

function updateGroupSummary(groups) {
  const target = document.getElementById('group-summary-text');
  if (!groups.length) {
    target.textContent = '';
    return;
  }

  target.textContent = `${groups.length} groups shown`;
}

function renderPartialAxesPlot() {
  const themeColors = getThemeColors();
  const partialAxes = (payload.partial_axes ?? []).filter(
    (entry) => entry.partial_axis === 1 || entry.partial_axis === 2
  );
  const hasPartialAxes = partialAxes.length > 0;
  const seriesKeys = [...new Set(partialAxes.map((entry) => `${entry.group}::${entry.partial_axis}`))];
  const palette = COLOR_PALETTES.Earth.colors;

  const traces = seriesKeys.map((seriesKey, index) => {
    const [group, partialAxisText] = seriesKey.split('::');
    const partialAxis = Number(partialAxisText);
    const seriesEntries = partialAxes.filter(
      (entry) => entry.group === group && entry.partial_axis === partialAxis
    );
    const vector = buildPartialAxesVector(seriesEntries);
    if (!vector) {
      return null;
    }

    const label = `Dim${partialAxis}.${group}`;

    return {
      type: 'scatter',
      mode: 'lines+markers+text',
      name: label,
      legendgroup: `axes:${seriesKey}`,
      x: [0, vector.x],
      y: [0, vector.y],
      text: ['', label],
      textposition: vector.x >= 0 ? 'middle right' : 'middle left',
      cliponaxis: false,
      textfont: {
        color: palette[index % palette.length],
        size: 12,
        family: '"IBM Plex Sans", "Helvetica Neue", sans-serif',
      },
      customdata: [
        '',
        seriesEntries
          .map(
            (entry) =>
              `${entry.group}<br>Partial axis ${entry.partial_axis}<br>${entry.global_dim}: ${formatValue(entry.value)}`
          )
          .join('<br>'),
      ],
      hovertemplate: '%{customdata}<extra></extra>',
      marker: {
        color: palette[index % palette.length],
        size: [0, 9],
        symbol: 'circle',
        line: {
          color: themeColors.markerLine,
          width: 1,
        },
      },
      line: {
        color: withAlpha(palette[index % palette.length], 0.7),
        width: 2,
      },
    };
  }).filter(Boolean);

  if (hasPartialAxes) {
    traces.unshift(buildPartialAxesCircleBoundary());
  }

  Plotly.react(
    'partial-axes-plot',
    hasPartialAxes ? traces : [],
    buildPartialAxesLayout(hasPartialAxes),
    {
      responsive: true,
      displaylogo: false,
      toImageButtonOptions: {
        format: 'png',
        filename: 'mfa-partial-axes',
        width: 1200,
        height: 700,
        scale: 2,
      },
      modeBarButtonsToAdd: [
        {
          name: 'Download SVG',
          icon: Plotly.Icons.camera,
          click: () => {
            downloadPlotImage('partial-axes-plot', 'mfa-partial-axes.svg', 'svg');
          },
        },
      ],
      modeBarButtonsToRemove: [
        'lasso2d',
        'select2d',
        'zoom2d',
        'pan2d',
        'zoomIn2d',
        'zoomOut2d',
        'autoScale2d',
        'resetScale2d',
      ],
    }
  );

  updatePartialAxesSummary(partialAxes);
}

function buildPartialAxesVector(groupEntries) {
  const xEntry = groupEntries.find((entry) => entry.global_dim === state.xDimension);
  const yEntry = groupEntries.find((entry) => entry.global_dim === state.yDimension);
  if (!xEntry || !yEntry) {
    return null;
  }

  return {
    x: xEntry.value,
    y: yEntry.value,
  };
}

function buildPartialAxesCircleBoundary() {
  const x = [];
  const y = [];
  for (let step = 0; step <= 120; step += 1) {
    const theta = (step / 120) * Math.PI * 2;
    x.push(Math.cos(theta));
    y.push(Math.sin(theta));
  }

  return {
    type: 'scatter',
    mode: 'lines',
    name: 'Unit circle',
    x,
    y,
    line: {
      color: withAlpha('#4B5563', 0.55),
      width: 2,
    },
    hoverinfo: 'skip',
    showlegend: false,
  };
}

function buildPartialAxesLayout(hasPartialAxes) {
  const themeColors = getThemeColors();
  return {
    paper_bgcolor: 'rgba(0, 0, 0, 0)',
    plot_bgcolor: 'rgba(255, 255, 255, 0)',
    margin: { t: 20, r: 48, b: 70, l: 80 },
    font: {
      color: themeColors.font,
      family: '"IBM Plex Sans", "Helvetica Neue", sans-serif',
    },
    showlegend: false,
    xaxis: {
      title: {
        text: dimensionsByKey[state.xDimension].label,
        font: { color: themeColors.font },
      },
      range: [-1.08, 1.3],
      constrain: 'domain',
      scaleanchor: 'y',
      scaleratio: 1,
      automargin: true,
      gridcolor: themeColors.grid,
      gridwidth: 1,
      zeroline: true,
      zerolinecolor: themeColors.zeroline,
      zerolinewidth: 1,
      tickfont: { color: themeColors.font },
    },
    yaxis: {
      title: {
        text: dimensionsByKey[state.yDimension].label,
        font: { color: themeColors.font },
      },
      range: [-1.16, 1.16],
      constrain: 'domain',
      automargin: true,
      gridcolor: themeColors.grid,
      gridwidth: 1,
      zeroline: true,
      zerolinecolor: themeColors.zeroline,
      zerolinewidth: 1,
      tickfont: { color: themeColors.font },
    },
    annotations: hasPartialAxes
      ? []
      : [
          {
            text: 'Partial axes values are not available.',
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

function updatePartialAxesSummary(partialAxes) {
  const target = document.getElementById('partial-axes-summary');
  if (!partialAxes.length) {
    target.textContent = '';
    return;
  }

  const groups = new Set(partialAxes.map((entry) => entry.group));
  const axes = new Set(partialAxes.map((entry) => `${entry.group}::${entry.partial_axis}`));
  target.textContent = `${axes.size} partial axes across ${groups.size} groups`;
}

function renderVariancePlot() {
  const components = payload.component_variance.filter(
    (component) => component.variance_explained !== null
  );
  const selectedDimensions = new Set([state.xDimension, state.yDimension]);
  const themeColors = getThemeColors();
  const hasVariance = components.length > 0;

  const barTrace = {
    type: 'bar',
    name: 'Explained variance',
    x: components.map((component) => component.label),
    y: components.map((component) => component.variance_explained * 100),
    marker: {
      color: components.map((component) =>
        selectedDimensions.has(component.key)
          ? SELECTED_DIMENSION_COLOR
          : DEFAULT_MARKER_COLOR
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
    hasVariance ? [barTrace] : [],
    buildVarianceLayout(hasVariance),
    {
      responsive: true,
      displaylogo: false,
      toImageButtonOptions: {
        format: 'png',
        filename: buildVarianceDownloadFilename('png').replace('.png', ''),
        width: 1200,
        height: 700,
        scale: 2,
      },
      modeBarButtonsToAdd: [
        {
          name: 'Download SVG',
          icon: Plotly.Icons.camera,
          click: () => {
            downloadPlotImage(
              'variance-plot',
              buildVarianceDownloadFilename('svg'),
              'svg'
            );
          },
        },
      ],
      modeBarButtonsToRemove: [
        'lasso2d',
        'select2d',
        'zoom2d',
        'pan2d',
        'zoomIn2d',
        'zoomOut2d',
        'autoScale2d',
        'resetScale2d',
      ],
    }
  );

  renderCumulativeVariancePlot(components, hasVariance, themeColors);
  updateVarianceSummary(components);
}

function renderCumulativeVariancePlot(components, hasVariance, themeColors) {
  let cumulativeTotal = 0;
  const selectedDimensions = new Set([state.xDimension, state.yDimension]);
  const cumulativeTrace = {
    type: 'scatter',
    mode: 'lines+markers',
    name: 'Cumulative explained variance',
    x: components.map((component) => component.label),
    y: components.map((component) => {
      cumulativeTotal += component.variance_explained * 100;
      return cumulativeTotal;
    }),
    line: {
      color: DEFAULT_MARKER_COLOR,
      width: 3,
    },
    marker: {
      color: components.map((component) =>
        selectedDimensions.has(component.key)
          ? SELECTED_DIMENSION_COLOR
          : DEFAULT_MARKER_COLOR
      ),
      size: 8,
      line: {
        color: themeColors.markerLine,
        width: 1,
      },
    },
    hovertemplate: '%{x}: %{y:.2f}% cumulative<extra></extra>',
  };

  Plotly.react(
    'cumulative-variance-plot',
    hasVariance ? [cumulativeTrace] : [],
    buildCumulativeVarianceLayout(hasVariance),
    {
      responsive: true,
      displaylogo: false,
      toImageButtonOptions: {
        format: 'png',
        filename: buildCumulativeVarianceDownloadFilename('png').replace('.png', ''),
        width: 1200,
        height: 700,
        scale: 2,
      },
      modeBarButtonsToAdd: [
        {
          name: 'Download SVG',
          icon: Plotly.Icons.camera,
          click: () => {
            downloadPlotImage(
              'cumulative-variance-plot',
              buildCumulativeVarianceDownloadFilename('svg'),
              'svg'
            );
          },
        },
      ],
      modeBarButtonsToRemove: [
        'lasso2d',
        'select2d',
        'zoom2d',
        'pan2d',
        'zoomIn2d',
        'zoomOut2d',
        'autoScale2d',
        'resetScale2d',
      ],
    }
  );
  updateCumulativeSummary(components);
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

function buildCumulativeVarianceLayout(hasVariance) {
  const themeColors = getThemeColors();
  return {
    paper_bgcolor: 'rgba(0, 0, 0, 0)',
    plot_bgcolor: 'rgba(255, 255, 255, 0)',
    margin: { t: 28, r: 56, b: 60, l: 80 },
    font: {
      color: themeColors.font,
      family: '"IBM Plex Sans", "Helvetica Neue", sans-serif',
    },
    xaxis: {
      showgrid: true,
      gridcolor: themeColors.gridSoft,
      gridwidth: 1,
      tickfont: { color: themeColors.font },
    },
    yaxis: {
      title: {
        text: 'Cumulative explained variance (%)',
        font: { color: themeColors.font },
      },
      range: [0, 104],
      gridcolor: themeColors.grid,
      gridwidth: 1,
      tickfont: { color: themeColors.font },
      zeroline: false,
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
    gridSoft: styles.getPropertyValue('--plot-grid-soft').trim(),
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

function buildPartialHoverText(entry) {
  return [
    `<b>${entry.sample_id}</b>`,
    `Group: ${entry.group}`,
    `${dimensionsByKey[state.xDimension].label}: ${formatValue(entry.coords[state.xDimension])}`,
    `${dimensionsByKey[state.yDimension].label}: ${formatValue(entry.coords[state.yDimension])}`,
  ].join('<br>');
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

function updateCumulativeSummary(components) {
  const finalValue = components.length
    ? components.reduce((sum, component) => sum + component.variance_explained, 0) * 100
    : null;
  document.getElementById('cumulative-summary').textContent = finalValue === null
    ? 'Cumulative variance unavailable'
    : `${formatValue(finalValue)}% at component ${components.length}`;
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
