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
  Symbols: {
    kind: 'categorical',
    colors: ['#6B7280'],
    symbols: ['square', 'triangle-up', 'circle', 'x', 'star'],
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
const DEFAULT_MARKER_COLOR = '#6B7280';
const VARIANCE_MARKER_COLOR = '#126782';
const SELECTED_DIMENSION_COLOR = '#083D5B';
const ELLIPSE_SCALE = 2.4477;
const PARTIAL_AXES_X_RANGE = [-1.08, 1.3];
const PARTIAL_AXES_Y_RANGE = [-1.19, 1.19];
const DEFAULT_LABEL_PLOT_WIDTH = 560;
const DEFAULT_LABEL_PLOT_HEIGHT = 420;
const MAX_FEATURE_OVERLAY_COUNT = 100;
const SAMPLE_LEGEND_MIN_RIGHT_MARGIN = 150;
const SAMPLE_LEGEND_MAX_RIGHT_MARGIN = 420;
const SAMPLE_LEGEND_SYMBOL_WIDTH = 46;
const SAMPLE_LEGEND_LABEL_PADDING = 34;
const SAMPLE_LEGEND_CHARACTER_WIDTH = 7.2;
const SAMPLE_NUMERIC_COLORBAR_Y = 1;
const SAMPLE_NUMERIC_COLORBAR_LENGTH = 0.28;
const SAMPLE_LEGEND_BELOW_COLORBAR_Y = 0.72;
const SECONDARY_SQUARE_PLOT_MARGIN = { t: 20, r: 46, b: 70, l: 80 };
const VARIANCE_PLOT_MARGIN = { t: 20, r: 20, b: 42, l: 80 };
const CUMULATIVE_VARIANCE_PLOT_MARGIN = { t: 28, r: 56, b: 42, l: 80 };

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
  showSampleScores: true,
  showBarycenter: false,
  showPartialOverlay: false,
  showFeatureCorrelations: false,
  showFullFeatureLabels: false,
  topFeatureCount: 10,
  featureLoadingScale: 1,
  pointSizeScale: 1,
  featureTableSort: {
    column: 'rankingScore',
    direction: 'desc',
  },
  featureLoadingGroups: new Set(payload.partial_groups),
  partialSampleGroups: new Set(payload.partial_groups),
  fontSize: 12,
  filters: [createDefaultSampleFilter()],
};

function createDefaultSampleFilter() {
  return {
    field: '',
    categoricalValues: new Set(),
    numericMin: null,
    numericMax: null,
  };
}

function initialize() {
  populateDimensionSelectors();
  populateColorControls();
  bindEvents();
  bindSamplePlotResizeObserver();
  renderFilterControls();
  renderPlot();
}

function bindSamplePlotResizeObserver() {
  const samplePlotShell = document.querySelector('.plot-shell-main');
  if (!samplePlotShell || !window.ResizeObserver) {
    return;
  }

  let resizeAnimationFrame = null;
  const resizeObserver = new ResizeObserver(() => {
    if (resizeAnimationFrame !== null) {
      window.cancelAnimationFrame(resizeAnimationFrame);
    }

    resizeAnimationFrame = window.requestAnimationFrame(() => {
      Plotly.Plots.resize('sample-plot');
      resizeAnimationFrame = null;
    });
  });
  resizeObserver.observe(samplePlotShell);
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
  document.getElementById('show-full-feature-labels').checked = state.showFullFeatureLabels;
  document.getElementById('top-feature-count').value = state.topFeatureCount;
  document.getElementById('feature-loading-scale').value = state.featureLoadingScale;
  document.getElementById('point-size-scale').value = state.pointSizeScale;
  document.getElementById('font-size').value = state.fontSize;
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

  document.getElementById('show-full-feature-labels').addEventListener('change', (event) => {
    state.showFullFeatureLabels = event.target.checked;
    renderPlot();
  });

  document.getElementById('top-feature-count').addEventListener('input', (event) => {
    const nextValue = Number(event.target.value);
    if (!Number.isFinite(nextValue) || nextValue < 1) {
      return;
    }
    state.topFeatureCount = Math.min(Math.floor(nextValue), MAX_FEATURE_OVERLAY_COUNT);
    event.target.value = state.topFeatureCount;
    renderPlot();
  });

  document.getElementById('feature-loading-scale').addEventListener('input', (event) => {
    const nextValue = Number(event.target.value);
    if (!Number.isFinite(nextValue) || nextValue < 1) {
      return;
    }
    state.featureLoadingScale = Math.floor(nextValue);
    event.target.value = state.featureLoadingScale;
    renderPlot();
  });

  document.getElementById('point-size-scale').addEventListener('input', (event) => {
    const nextValue = Number(event.target.value);
    if (!Number.isFinite(nextValue) || nextValue < 0.5) {
      return;
    }
    state.pointSizeScale = Math.min(nextValue, 1.5);
    event.target.value = state.pointSizeScale;
    renderPlot();
  });

  document.getElementById('font-size').addEventListener('input', (event) => {
    const nextValue = Math.round(Number(event.target.value));
    if (!Number.isFinite(nextValue) || nextValue < 8) {
      return;
    }
    state.fontSize = Math.min(nextValue, 24);
    event.target.value = state.fontSize;
    renderPlot();
  });

  document.querySelectorAll('[data-feature-sort]').forEach((button) => {
    button.addEventListener('click', (event) => {
      updateFeatureTableSort(event.currentTarget);
      renderTopFeaturesTable();
    });
  });

  document.getElementById('download-feature-table').addEventListener('click', () => {
    downloadFeatureTableTsv();
  });

}

function renderFilterControls() {
  const container = document.getElementById('filter-controls');
  container.replaceChildren();

  container.appendChild(buildFeatureLoadingsRow());
  container.appendChild(buildPartialCoordinatesRow());

  state.filters.forEach((filter, index) => {
    container.appendChild(buildSampleFilterRow(filter, index));
  });

  const addRow = document.createElement('div');
  addRow.className = 'filter-row';

  const addButton = document.createElement('button');
  addButton.className = 'filter-add';
  addButton.type = 'button';
  addButton.textContent = 'Add filter...';
  addButton.style.gridColumn = '2';
  addButton.addEventListener('click', () => {
    state.filters.push(createDefaultSampleFilter());
    renderFilterControls();
  });
  addRow.appendChild(addButton);
  container.appendChild(addRow);
}

function buildOverlayToggle(labelText, checked, onChange, tooltipText) {
  const label = document.createElement('label');
  label.className = 'toggle-option';

  const input = document.createElement('input');
  input.type = 'checkbox';
  input.checked = checked;
  input.addEventListener('change', (event) => onChange(event.target.checked));

  const span = document.createElement('span');
  span.textContent = labelText;

  label.appendChild(input);
  label.appendChild(span);

  if (tooltipText) {
    const help = document.createElement('span');
    help.className = 'help-tooltip';
    help.tabIndex = 0;
    help.setAttribute('role', 'button');
    help.setAttribute('aria-label', `${labelText} help`);
    help.setAttribute('data-tooltip', tooltipText);
    help.textContent = '?';
    label.appendChild(help);
  }

  return label;
}

function buildGroupTogglesContainer(selectedGroups, disabled) {
  const container = document.createElement('div');
  container.className = 'filter-options';
  (payload.partial_groups || []).forEach((group) => {
    container.appendChild(
      buildCheckboxFilterOption(group, group, selectedGroups.has(group), selectedGroups, disabled)
    );
  });
  return container;
}

function buildFeatureLoadingsRow() {
  const row = document.createElement('div');
  row.className = 'filter-row';

  const toggle = buildOverlayToggle(
    'Feature loadings',
    state.showFeatureCorrelations,
    (checked) => {
      state.showFeatureCorrelations = checked;
      if (checked) state.featureLoadingGroups = new Set(payload.partial_groups);
      renderFilterControls();
      renderPlot();
    },
    'Overlays the strongest feature correlations from feature-correlations.tsv for the selected axes. Arrows point toward samples associated with higher feature values; longer arrows mean stronger representation in this two-dimensional view. Features are ordered by plane magnitude, calculated as sqrt(x^2 + y^2) from the current X and Y correlation values.'
  );
  row.appendChild(toggle);

  const groups = buildGroupTogglesContainer(state.featureLoadingGroups, !state.showFeatureCorrelations);
  groups.style.gridColumn = '2 / -1';
  row.appendChild(groups);

  return row;
}

function buildPartialCoordinatesRow() {
  const row = document.createElement('div');
  row.className = 'filter-row';

  const toggle = buildOverlayToggle(
    'Partial coordinates',
    state.showPartialOverlay,
    (checked) => {
      state.showPartialOverlay = checked;
      if (checked) state.partialSampleGroups = new Set(payload.partial_groups);
      renderFilterControls();
      renderPlot();
    },
    "Shows each sample's group-specific partial coordinates from partial-sample-coordinates.tsv and connects them to the global sample scores from ordination.txt. Long connectors indicate that a group places that sample away from the consensus position."
  );
  row.appendChild(toggle);

  const groups = buildGroupTogglesContainer(state.partialSampleGroups, !state.showPartialOverlay);
  groups.style.gridColumn = '2 / -1';
  row.appendChild(groups);

  return row;
}

function buildSampleFilterRow(filter, index) {
  const row = document.createElement('div');
  row.className = 'filter-row';
  const isFirstRow = index === 0;
  const isNumeric = filter.field && metadataByName[filter.field]?.type === 'numeric';

  if (isFirstRow) {
    const toggle = buildOverlayToggle(
      'Sample scores',
      state.showSampleScores,
      (checked) => {
        state.showSampleScores = checked;
        renderPlot();
      },
      'Shows the global MFA sample coordinates from ordination.txt on the selected X and Y axes. Each point is one sample score; coloring and sample filters use the sample metadata table provided to the visualizer. These scores are calculated from the input feature tables during the MFA action, then stored in the ordination results.'
    );
    row.appendChild(toggle); // col 1

    const fieldSelect = buildSampleMetadataSelect(filter);
    fieldSelect.style.gridColumn = '2';
    row.appendChild(fieldSelect);

    if (isNumeric) {
      const column = metadataByName[filter.field];
      if (filter.numericMin === null) { filter.numericMin = column.min; filter.numericMax = column.max; }
      const minCell = buildNumericFilterCell('Min:', filter.numericMin, (v) => { filter.numericMin = v; renderPlot(); });
      minCell.style.gridColumn = '3';
      row.appendChild(minCell);
      const maxCell = buildNumericFilterCell('Max:', filter.numericMax, (v) => { filter.numericMax = v; renderPlot(); });
      maxCell.style.gridColumn = '4';
      row.appendChild(maxCell);
    } else {
      const valueControls = buildFilterValueControls(filter);
      valueControls.style.gridColumn = '3 / -1';
      row.appendChild(valueControls);
    }
  } else {
    const fieldSelect = buildSampleMetadataSelect(filter);
    fieldSelect.style.gridColumn = '2';
    row.appendChild(fieldSelect);

    if (isNumeric) {
      const column = metadataByName[filter.field];
      if (filter.numericMin === null) { filter.numericMin = column.min; filter.numericMax = column.max; }
      const minCell = buildNumericFilterCell('Min:', filter.numericMin, (v) => { filter.numericMin = v; renderPlot(); });
      minCell.style.gridColumn = '3';
      row.appendChild(minCell);
      const maxCell = buildNumericFilterCell('Max:', filter.numericMax, (v) => { filter.numericMax = v; renderPlot(); });
      maxCell.style.gridColumn = '4';
      row.appendChild(maxCell);
    } else {
      const valueControls = buildFilterValueControls(filter);
      valueControls.style.gridColumn = '3 / 6';
      row.appendChild(valueControls);
    }

    const removeButton = buildFilterRemoveButton(index);
    removeButton.style.gridColumn = isNumeric ? '5' : '6';
    row.appendChild(removeButton);
  }

  return row;
}

function buildSampleMetadataSelect(filter) {
  const select = document.createElement('select');
  select.add(new Option('Select metadata…', ''));
  payload.metadata_columns.forEach((column) => {
    select.add(new Option(column.name, column.name));
  });
  select.value = filter.field;
  select.addEventListener('change', (event) => {
    filter.field = event.target.value;
    filter.categoricalValues = new Set();
    filter.numericMin = null;
    filter.numericMax = null;
    renderFilterControls();
    renderPlot();
  });
  return select;
}

function buildNumericFilterCell(labelText, value, onInput) {
  const cell = document.createElement('div');
  cell.className = 'filter-numeric-cell';

  const label = document.createElement('span');
  label.className = 'filter-numeric-label';
  label.textContent = labelText;
  cell.appendChild(label);

  const input = document.createElement('input');
  input.type = 'number';
  input.step = 'any';
  input.value = value;
  input.addEventListener('input', (event) => {
    const nextValue = event.target.value === '' ? null : Number(event.target.value);
    onInput(nextValue);
  });
  cell.appendChild(input);

  return cell;
}

function buildFilterValueControls(filter) {
  const container = document.createElement('div');
  container.className = 'filter-values';

  if (!filter.field) {
    return container;
  }

  const column = metadataByName[filter.field];
  renderCategoricalFilterControls(container, filter, column);
  return container;
}

function buildFilterRemoveButton(index) {
  const button = document.createElement('button');
  button.className = 'filter-remove';
  button.type = 'button';
  button.textContent = 'x';
  button.addEventListener('click', () => {
    state.filters.splice(index, 1);
    renderFilterControls();
    renderPlot();
  });
  return button;
}

function renderCategoricalFilterControls(container, filter, column) {
  if (!filter.categoricalValues.size) {
    column.values.forEach((value) => filter.categoricalValues.add(value));
    if (column.has_missing) {
      filter.categoricalValues.add(MISSING_VALUE_TOKEN);
    }
  }

  const options = document.createElement('div');
  options.className = 'filter-options';

  column.values.forEach((value) => {
    options.appendChild(
      buildCheckboxFilterOption(
        value,
        value,
        filter.categoricalValues.has(value),
        filter.categoricalValues
      )
    );
  });

  if (column.has_missing) {
    options.appendChild(
      buildCheckboxFilterOption(
        MISSING_VALUE_TOKEN,
        'Missing',
        filter.categoricalValues.has(MISSING_VALUE_TOKEN),
        filter.categoricalValues
      )
    );
  }

  container.appendChild(options);
}

function buildCheckboxFilterOption(value, label, checked, selectedValues, disabled = false) {
  const wrapper = document.createElement('label');
  wrapper.className = disabled ? 'filter-option filter-option-disabled' : 'filter-option';

  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.checked = checked;
  checkbox.disabled = disabled;
  checkbox.value = value;
  if (!disabled) {
    checkbox.addEventListener('change', (event) => {
      if (event.target.checked) {
        selectedValues.add(value);
      } else {
        selectedValues.delete(value);
      }
      renderPlot();
    });
  }

  const text = document.createElement('span');
  text.textContent = label;

  wrapper.appendChild(checkbox);
  wrapper.appendChild(text);
  return wrapper;
}


function getFilteredSamples() {
  return payload.samples.filter((sample) =>
    state.filters.every((filter) => samplePassesFilter(sample, filter))
  );
}

function samplePassesFilter(sample, filter) {
  if (!filter.field) {
    return true;
  }

  const column = metadataByName[filter.field];
  const value = sample.metadata[filter.field];
  if (column.type === 'categorical') {
    const normalizedValue = value === null ? MISSING_VALUE_TOKEN : value;
    return filter.categoricalValues.has(normalizedValue);
  }

  if (value === null) {
    return false;
  }

  const lowerBound = filter.numericMin ?? column.min;
  const upperBound = filter.numericMax ?? column.max;
  return value >= lowerBound && value <= upperBound;
}

function renderPlot() {
  const filteredSamples = getFilteredSamples();
  const traces = buildTraces(filteredSamples);
  const layout = buildLayout(traces);
  updateSamplePlotResizeLimits(layout);

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
  renderTopFeaturesTable();
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
    (paletteName) =>
      COLOR_PALETTES[paletteName].kind === paletteKind &&
      isColorPaletteAvailable(paletteName)
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

function isColorPaletteAvailable(paletteName) {
  if (paletteName !== 'Symbols') {
    return true;
  }

  const colorColumn = metadataByName[state.colorBy];
  return (
    colorColumn?.type === 'categorical' &&
    getCategoricalLevelCount(colorColumn) <= COLOR_PALETTES.Symbols.symbols.length
  );
}

function getCategoricalLevelCount(colorColumn) {
  return colorColumn.values.length + Number(colorColumn.has_missing);
}

function getOrderedGroupNames() {
  return payload.partial_groups;
}

function getGroupColorMap(groups = getOrderedGroupNames()) {
  const orderedGroups = [...new Set(groups)];
  return Object.fromEntries(
    orderedGroups.map((group, index) => [
      group,
      COLOR_PALETTES.Safe.colors[index % COLOR_PALETTES.Safe.colors.length],
    ])
  );
}

function buildTraces(samples) {
  const colorColumn = metadataByName[state.colorBy];
  const partialOverlayTraces = buildPartialOverlayTraces(samples, colorColumn);
  const featureCorrelationTraces = buildFeatureCorrelationTraces();
  const sampleScoreTraces = buildSampleScoreTraces(samples, colorColumn);
  return appendBarycenterTraces(
    [...sampleScoreTraces, ...partialOverlayTraces, ...featureCorrelationTraces],
    samples,
    colorColumn
  );
}

function buildSampleScoreTraces(samples, colorColumn) {
  if (!state.showSampleScores) {
    return [];
  }

  if (!colorColumn) {
    return [buildSingleTrace(samples, DEFAULT_MARKER_COLOR, 'Samples')];
  }

  if (colorColumn.type === 'numeric') {
    return buildNumericTraces(samples, colorColumn);
  }

  return buildCategoricalTraces(samples, colorColumn);
}

function buildFeatureCorrelationTraces() {
  if (!state.showFeatureCorrelations) {
    return [];
  }

  const themeColors = getThemeColors();
  const rankedFeatures = getRankedFeatureCorrelations(
    state.topFeatureCount,
    getAllowedGroups('feature_loadings')
  );
  if (!rankedFeatures.length) {
    return [];
  }

  const groupOrder = [...new Set(rankedFeatures.map((feature) => feature.group))].sort();
  const groupColors = getGroupColorMap(groupOrder);
  const labelPlacement = placeFeatureCorrelationLabels(rankedFeatures, groupColors);

  const traces = [];
  groupOrder.forEach((group) => {
    const groupFeatures = rankedFeatures.filter((feature) => feature.group === group);
    if (!groupFeatures.length) {
      return;
    }
    const groupLegend = `feature-correlations:${group}`;
    const groupLabelPlacement = labelPlacement.filter((label) => label.group === group);

    const lineX = [];
    const lineY = [];
    groupFeatures.forEach((feature) => {
      lineX.push(0, feature.plotX, null);
      lineY.push(0, feature.plotY, null);
    });

    traces.push({
      type: 'scatter',
      mode: 'lines',
      name: `${group} feature vectors`,
      legendgroup: groupLegend,
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
      type: 'scatter',
      mode: 'markers',
      name: `${group} (n=${groupFeatures.length})`,
      legendgroup: groupLegend,
      showlegend: true,
      x: [null],
      y: [null],
      hoverinfo: 'skip',
      marker: {
        color: groupColors[group],
        size: scalePointSize(9),
        opacity: 0.95,
        symbol: 'triangle-up',
        line: {
          color: themeColors.markerLine,
          width: 1,
        },
      },
    });

    traces.push({
      type: 'scatter',
      mode: 'markers',
      name: `${group} feature loading endpoints`,
      legendgroup: groupLegend,
      showlegend: false,
      x: groupFeatures.map((feature) => feature.plotX),
      y: groupFeatures.map((feature) => feature.plotY),
      hovertemplate:
        '<b>%{customdata[0]}</b><br>' +
        'Group: %{customdata[1]}<br>' +
        `${state.xDimension}: %{customdata[2]:.3f}<br>` +
        `${state.yDimension}: %{customdata[3]:.3f}<br>` +
        'Plane magnitude: %{customdata[4]:.3f}<extra></extra>',
      customdata: groupFeatures.map((feature) => [
        feature.feature_name,
        feature.group,
        feature.x,
        feature.y,
        feature.rankingScore,
      ]),
      marker: {
        color: groupColors[group],
        size: scalePointSize(9),
        opacity: 0.95,
        symbol: 'triangle-up',
        angle: groupFeatures.map((feature) => featureLoadingMarkerAngle(feature)),
        line: {
          color: themeColors.markerLine,
          width: 1,
        },
      },
    });

    traces.push(...buildPlotLabelConnectorTraces(groupLabelPlacement, {
      legendgroup: groupLegend,
    }));
    const labelTrace = buildPlotLabelTrace(groupLabelPlacement, state.fontSize, {
      legendgroup: groupLegend,
      name: `${group} feature labels`,
    });
    if (labelTrace) {
      traces.push(labelTrace);
    }
  });

  return traces;
}

function featureLoadingMarkerAngle(feature) {
  const angleFromXAxis = Math.atan2(feature.plotY, feature.plotX) * 180 / Math.PI;
  return 90 - angleFromXAxis;
}

function getRankedFeatureCorrelations(limit = null, allowedFeatureGroups = null) {
  // Rank by correlation magnitude in the currently displayed 2D plane so the
  // overlay surfaces the variables best represented in the exact view the user
  // is inspecting.
  const featureCorrelations = allowedFeatureGroups === null
    ? payload.feature_correlations
    : payload.feature_correlations.filter((feature) => allowedFeatureGroups.has(feature.group));
  const rankedFeatures = featureCorrelations
    .map((feature) => ({
      ...feature,
      x: feature.coords[state.xDimension],
      y: feature.coords[state.yDimension],
    }))
    .filter((feature) => Number.isFinite(feature.x) && Number.isFinite(feature.y))
    .map((feature) => ({
      ...feature,
      rankingScore: Math.hypot(feature.x, feature.y),
      display_feature_name: shortenTaxonomyFeatureName(feature.feature_name),
      plot_feature_name: formatFeaturePlotLabel(feature.feature_name),
    }))
    .sort((a, b) =>
      b.rankingScore - a.rankingScore ||
      a.group.localeCompare(b.group) ||
      a.display_feature_name.localeCompare(b.display_feature_name)
    )
    .map((feature, index) => ({
      ...feature,
      rank: index + 1,
      plotX: feature.x * state.featureLoadingScale,
      plotY: feature.y * state.featureLoadingScale,
    }));

  return limit === null ? rankedFeatures : rankedFeatures.slice(0, limit);
}

function getAllowedGroups(target) {
  if (target === 'feature_loadings') {
    return state.showFeatureCorrelations ? state.featureLoadingGroups : new Set();
  }
  if (target === 'partial_samples') {
    return state.showPartialOverlay ? state.partialSampleGroups : new Set();
  }
  return new Set(payload.partial_groups);
}

function getSortedFeatureTableRows() {
  const features = getRankedFeatureCorrelations(null, null);
  const { column, direction } = state.featureTableSort;
  return features
    .slice()
    .sort((left, right) => compareFeatureTableRows(left, right, column, direction))
    .slice(0, MAX_FEATURE_OVERLAY_COUNT);
}

function compareFeatureTableRows(left, right, column, direction) {
  let comparison;
  if (['x', 'y', 'rankingScore'].includes(column)) {
    comparison = left[column] - right[column];
  } else if (column === 'feature_name') {
    comparison = left.display_feature_name.localeCompare(right.display_feature_name);
  } else {
    comparison = String(left[column]).localeCompare(String(right[column]));
  }

  if (comparison !== 0) {
    return direction === 'asc' ? comparison : -comparison;
  }

  return left.rank - right.rank;
}

function updateFeatureTableSort(button) {
  const column = button.dataset.featureSort;
  if (state.featureTableSort.column === column) {
    state.featureTableSort.direction =
      state.featureTableSort.direction === 'asc' ? 'desc' : 'asc';
    return;
  }

  state.featureTableSort = {
    column,
    direction: button.dataset.defaultDirection ?? 'asc',
  };
}

function renderTopFeaturesTable() {
  const body = document.getElementById('top-features-table-body');
  const empty = document.getElementById('top-features-empty');
  if (!body || !empty) {
    return;
  }

  const xHeading = document.getElementById('feature-table-x-heading');
  const yHeading = document.getElementById('feature-table-y-heading');
  if (xHeading) {
    xHeading.textContent = dimensionsByKey[state.xDimension].label;
  }
  if (yHeading) {
    yHeading.textContent = dimensionsByKey[state.yDimension].label;
  }

  body.replaceChildren();
  const features = getSortedFeatureTableRows();
  updateFeatureTableSortHeaders();
  empty.textContent = features.length ? '' : 'No finite feature correlations for the selected dimensions.';

  const fragment = document.createDocumentFragment();
  features.forEach((feature) => {
    const row = document.createElement('tr');
    row.appendChild(buildFeatureNameCell(feature));
    row.appendChild(buildFeatureTableCell(feature.group));
    row.appendChild(buildFeatureTableCell(formatValue(feature.x), 'feature-table-number'));
    row.appendChild(buildFeatureTableCell(formatValue(feature.y), 'feature-table-number'));
    row.appendChild(
      buildFeatureTableCell(formatValue(feature.rankingScore), 'feature-table-number')
    );
    fragment.appendChild(row);
  });
  body.appendChild(fragment);
}

function updateFeatureTableSortHeaders() {
  document.querySelectorAll('[data-feature-sort]').forEach((button) => {
    const column = button.dataset.featureSort;
    const isActive = column === state.featureTableSort.column;
    const direction = isActive ? state.featureTableSort.direction : 'none';
    const header = button.closest('th');
    const indicator = button.querySelector('.feature-table-sort-indicator');
    header.setAttribute(
      'aria-sort',
      direction === 'none'
        ? 'none'
        : direction === 'asc'
          ? 'ascending'
          : 'descending'
    );
    button.classList.toggle('is-active', isActive);
    indicator.textContent = isActive
      ? state.featureTableSort.direction === 'asc'
        ? '↑'
        : '↓'
      : '';
  });
}

function buildFeatureNameCell(feature) {
  const tooltipText = feature.feature_name;
  const cell = buildFeatureTableCell(feature.display_feature_name, 'feature-name-cell');
  cell.tabIndex = 0;
  cell.addEventListener('mouseenter', (event) => {
    showFeatureNameTooltip(tooltipText, event.clientX, event.clientY);
  });
  cell.addEventListener('mousemove', (event) => {
    positionFeatureNameTooltip(event.clientX, event.clientY);
  });
  cell.addEventListener('mouseleave', hideFeatureNameTooltip);
  cell.addEventListener('focus', () => {
    const rect = cell.getBoundingClientRect();
    showFeatureNameTooltip(tooltipText, rect.left, rect.bottom);
  });
  cell.addEventListener('blur', hideFeatureNameTooltip);
  return cell;
}

function showFeatureNameTooltip(text, clientX, clientY) {
  const tooltip = document.getElementById('feature-name-tooltip');
  if (!tooltip || !text) {
    return;
  }

  tooltip.textContent = text;
  tooltip.classList.add('is-visible');
  positionFeatureNameTooltip(clientX, clientY);
}

function positionFeatureNameTooltip(clientX, clientY) {
  const tooltip = document.getElementById('feature-name-tooltip');
  if (!tooltip || !tooltip.classList.contains('is-visible')) {
    return;
  }

  const offset = 12;
  const rect = tooltip.getBoundingClientRect();
  const x = Math.min(clientX + offset, window.innerWidth - rect.width - offset);
  const y = Math.min(clientY + offset, window.innerHeight - rect.height - offset);
  tooltip.style.left = `${Math.max(offset, x)}px`;
  tooltip.style.top = `${Math.max(offset, y)}px`;
}

function hideFeatureNameTooltip() {
  const tooltip = document.getElementById('feature-name-tooltip');
  if (!tooltip) {
    return;
  }

  tooltip.classList.remove('is-visible');
}

function buildFeatureTableCell(value, className) {
  const cell = document.createElement('td');
  if (className) {
    cell.className = className;
  }
  cell.textContent = value;
  return cell;
}

function downloadFeatureTableTsv() {
  const rows = getSortedFeatureTableRows();
  const xLabel = dimensionsByKey[state.xDimension].label;
  const yLabel = dimensionsByKey[state.yDimension].label;
  const header = [
    'feature',
    'feature_id',
    'group',
    xLabel,
    yLabel,
    'plane_magnitude',
  ];
  const lines = [
    header.map(escapeTsvValue).join('\t'),
    ...rows.map((feature) => [
      feature.display_feature_name,
      feature.feature_id,
      feature.group,
      feature.x,
      feature.y,
      feature.rankingScore,
    ].map(escapeTsvValue).join('\t')),
  ];

  const blob = new Blob([`${lines.join('\n')}\n`], { type: 'text/tab-separated-values' });
  const link = document.createElement('a');
  const objectUrl = URL.createObjectURL(blob);
  link.href = objectUrl;
  link.download = buildFeatureTableDownloadFilename();
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

function escapeTsvValue(value) {
  return String(value).replace(/\t/g, ' ').replace(/\r?\n/g, ' ');
}

function buildFeatureTableDownloadFilename() {
  const xLabel = state.xDimension.toLowerCase().replace(/\s+/g, '-');
  const yLabel = state.yDimension.toLowerCase().replace(/\s+/g, '-');
  return `mfa-contributing-features-${xLabel}-vs-${yLabel}.tsv`;
}

function formatFeaturePlotLabel(featureName) {
  if (state.showFullFeatureLabels) {
    return featureName;
  }

  return shortenTaxonomyFeatureName(featureName);
}

function shortenTaxonomyFeatureName(featureName) {
  const ranks = String(featureName)
    .split(';')
    .map((rank) => rank.trim())
    .filter(Boolean);
  if (ranks.length < 2) {
    return featureName;
  }

  const lastRank = ranks[ranks.length - 1];
  if (!/^[a-z]__/.test(lastRank)) {
    return featureName;
  }

  const shortened = lastRank.replace(/^[kpcofgs]__/, '').trim();
  return shortened || featureName;
}

function buildPartialOverlayTraces(samples, colorColumn) {
  if (
    !state.showPartialOverlay ||
    !payload.partial_samples?.length
  ) {
    return [];
  }

  const visibleSampleIds = new Set(samples.map((sample) => sample.sample_id));
  const allowedPartialGroups = getAllowedGroups('partial_samples');
  const visibleSamplesById = Object.fromEntries(
    samples.map((sample) => [sample.sample_id, sample])
  );
  const visiblePartialSamples = payload.partial_samples.filter(
    (entry) =>
      allowedPartialGroups.has(entry.group) &&
      visibleSampleIds.has(entry.sample_id) &&
      entry.coords[state.xDimension] !== undefined &&
      entry.coords[state.yDimension] !== undefined
  );

  if (!visiblePartialSamples.length) {
    return [];
  }

  const groupColors = getGroupColorMap();
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
      payload.partial_groups.forEach((group) => {
        const groupEntries = visiblePartialSamples.filter(
          (entry) => entry.group === group && categorySampleIds.has(entry.sample_id)
        );
        if (!groupEntries.length) {
          return;
        }

        const color = groupColors[group];
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

  payload.partial_groups.forEach((group) => {
    const groupEntries = visiblePartialSamples.filter((entry) => entry.group === group);
    if (!groupEntries.length) {
      return;
    }

    const color = groupColors[group];
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
    type: 'scatter',
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
    type: 'scatter',
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
      size: scalePointSize(8),
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
    name: formatSampleLegendName(name, samples),
    legendgroup: options.legendgroup,
    showlegend: options.showlegend ?? true,
    x: samples.map((sample) => sample.coords[state.xDimension]),
    y: samples.map((sample) => sample.coords[state.yDimension]),
    customdata: samples.map(buildHoverText),
    hovertemplate: '%{customdata}<extra></extra>',
    marker: {
      color,
      size: scalePointSize(8),
      opacity: 0.9,
      symbol: options.symbol ?? 'circle',
      line: { color: getThemeColors().markerLine, width: 1 },
    },
  };
}

function formatSampleLegendName(name, samples) {
  return `${name} (n=${samples.length})`;
}

function scalePointSize(baseSize) {
  return baseSize * state.pointSizeScale;
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
      name: formatSampleLegendName(colorColumn.name, numericSamples),
      showlegend: false,
      x: numericSamples.map((sample) => sample.coords[state.xDimension]),
      y: numericSamples.map((sample) => sample.coords[state.yDimension]),
      customdata: numericSamples.map(buildHoverText),
      hovertemplate: '%{customdata}<extra></extra>',
      marker: {
        color: numericSamples.map((sample) => sample.metadata[colorColumn.name]),
        colorscale: getNumericColorscale(state.colorPalette),
        colorbar: {
          title: {
            text: formatSampleLegendName(colorColumn.name, numericSamples),
            font: { color: themeColors.font, size: themeColors.fontSize },
          },
          x: 1.02,
          xanchor: 'left',
          y: SAMPLE_NUMERIC_COLORBAR_Y,
          yanchor: 'top',
          len: SAMPLE_NUMERIC_COLORBAR_LENGTH,
          thickness: 18,
          tickfont: { color: themeColors.font, size: themeColors.fontSize },
        },
        size: scalePointSize(8),
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
  const palette = getCategoricalColors(getCategoricalLevelCount(colorColumn));
  const symbols = getCategoricalSymbols(getCategoricalLevelCount(colorColumn));
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
        symbol: symbols[index % symbols.length],
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

function getCategoricalSymbols(count) {
  const palette = COLOR_PALETTES[state.colorPalette] ?? COLOR_PALETTES.Plotly;
  const symbols = palette.symbols ?? ['circle'];
  return Array.from({ length: count }, (_, index) => symbols[index % symbols.length]);
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

function buildLayout(traces) {
  const themeColors = getThemeColors();
  const legendRightMargin = computeSampleLegendRightMargin(traces);
  const legendY = hasSampleNumericColorbar(traces) ? SAMPLE_LEGEND_BELOW_COLORBAR_Y : 1;
  const sharedGridStep = computeSharedSampleGridStep(traces);

  return {
    paper_bgcolor: 'rgba(0, 0, 0, 0)',
    plot_bgcolor: 'rgba(255, 255, 255, 0)',
    dragmode: 'zoom',
    hovermode: 'closest',
    margin: { t: 32, r: legendRightMargin, b: 78, l: 80 },
    font: {
      color: themeColors.font,
      family: 'Arial, sans-serif',
      size: themeColors.fontSize,
    },
    legend: {
      orientation: 'v',
      groupclick: 'togglegroup',
      yanchor: 'top',
      y: legendY,
      xanchor: 'left',
      x: 1.02,
      font: { color: themeColors.font, size: themeColors.fontSize },
    },
    xaxis: {
      title: {
        text: dimensionsByKey[state.xDimension].axis_title,
        font: { color: themeColors.font, size: themeColors.fontSize },
      },
      scaleanchor: 'y',
      scaleratio: 1,
      tickmode: 'linear',
      tick0: 0,
      dtick: sharedGridStep,
      zeroline: true,
      zerolinecolor: themeColors.zeroline,
      zerolinewidth: 1,
      gridcolor: themeColors.grid,
      gridwidth: 1,
      tickfont: { color: themeColors.font, size: themeColors.fontSize },
    },
    yaxis: {
      title: {
        text: dimensionsByKey[state.yDimension].axis_title,
        font: { color: themeColors.font, size: themeColors.fontSize },
      },
      tickmode: 'linear',
      tick0: 0,
      dtick: sharedGridStep,
      zeroline: true,
      zerolinecolor: themeColors.zeroline,
      zerolinewidth: 1,
      gridcolor: themeColors.grid,
      gridwidth: 1,
      tickfont: { color: themeColors.font, size: themeColors.fontSize },
    },
  };
}

function computeSharedSampleGridStep(traces) {
  const values = traces.flatMap((trace) => [
    ...extractFiniteTraceValues(trace.x),
    ...extractFiniteTraceValues(trace.y),
  ]);
  if (!values.length) {
    return 1;
  }

  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const span = Math.max(maxValue - minValue, 1e-12);
  return computeNiceTickStep(span / 10);
}

function extractFiniteTraceValues(values) {
  if (!Array.isArray(values)) {
    return [];
  }

  return values.filter((value) => Number.isFinite(value));
}

function computeNiceTickStep(rawStep) {
  const exponent = Math.floor(Math.log10(rawStep));
  const magnitude = 10 ** exponent;
  const normalized = rawStep / magnitude;

  if (normalized <= 1) {
    return magnitude;
  }
  if (normalized <= 2) {
    return 2 * magnitude;
  }
  if (normalized <= 5) {
    return 5 * magnitude;
  }
  return 10 * magnitude;
}

function hasSampleNumericColorbar(traces) {
  return traces.some((trace) => trace.marker?.colorbar);
}

function updateSamplePlotResizeLimits(layout) {
  const samplePlotShell = document.querySelector('.plot-shell-main');
  const samplePlot = document.getElementById('sample-plot');
  if (!samplePlotShell || !samplePlot) {
    return;
  }

  const shellWidth = samplePlotShell.getBoundingClientRect().width;
  const plotWidth = samplePlot.getBoundingClientRect().width;
  const shellExtraWidth = Math.max(shellWidth - plotWidth, 0);
  const plotHeight = samplePlot.getBoundingClientRect().height || 682;
  const squarePlotWidth = Math.max(
    plotHeight - layout.margin.t - layout.margin.b,
    0
  );
  const minimumShellWidth = Math.ceil(
    squarePlotWidth + layout.margin.l + layout.margin.r + shellExtraWidth
  );

  samplePlotShell.style.minWidth = `min(${minimumShellWidth}px, 100%)`;
}

function computeSampleLegendRightMargin(traces) {
  const legendLabels = traces.flatMap((trace) => {
    const labels = [];
    if (trace.showlegend !== false && trace.name) {
      labels.push(trace.name);
    }

    const colorbarTitle = trace.marker?.colorbar?.title?.text;
    if (colorbarTitle) {
      labels.push(colorbarTitle);
    }

    return labels;
  });

  const maxLabelCharacters = Math.max(
    0,
    ...legendLabels.map((label) => Array.from(String(label)).length)
  );
  const estimatedMargin = Math.ceil(
    SAMPLE_LEGEND_SYMBOL_WIDTH +
    SAMPLE_LEGEND_LABEL_PADDING +
    maxLabelCharacters * SAMPLE_LEGEND_CHARACTER_WIDTH
  );

  return clamp(
    estimatedMargin,
    SAMPLE_LEGEND_MIN_RIGHT_MARGIN,
    SAMPLE_LEGEND_MAX_RIGHT_MARGIN
  );
}

function renderGroupPlot() {
  const themeColors = getThemeColors();
  const groups = (payload.group_summary ?? []).filter(
    (entry) =>
      entry.coords[state.xDimension] !== undefined &&
      entry.coords[state.yDimension] !== undefined
  );
  const groupColors = getGroupColorMap(groups.map((entry) => entry.group));
  const labelPlacement = placeGroupInertiaLabels(groups, groupColors);

  const trace = {
    type: 'scatter',
    mode: 'markers',
    name: 'Groups',
    x: groups.map((entry) => entry.coords[state.xDimension]),
    y: groups.map((entry) => entry.coords[state.yDimension]),
    text: groups.map((entry) => entry.group),
    hovertemplate: '%{text}<br>%{customdata}<extra></extra>',
    customdata: groups.map(buildGroupHoverText),
    marker: {
      color: groups.map((entry) => groupColors[entry.group]),
      size: 14,
      symbol: 'diamond',
      line: {
        color: themeColors.markerLine,
        width: 1.5,
      },
    },
  };
  const traces = [
    trace,
    ...buildPlotLabelConnectorTraces(labelPlacement),
  ];
  const labelTrace = buildPlotLabelTrace(labelPlacement, state.fontSize);
  if (labelTrace) {
    traces.push(labelTrace);
  }

  Plotly.react(
    'group-plot',
    traces,
    buildGroupLayout(),
    {
      responsive: true,
      displaylogo: false,
      toImageButtonOptions: {
        format: 'png',
        filename: 'mfa-group-partial-inertia',
        width: 1200,
        height: 1200,
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
  ].join('<br>');
}

function placeGroupInertiaLabels(groups, groupColors) {
  const items = groups.map((entry) => ({
    anchorX: entry.coords[state.xDimension],
    anchorY: entry.coords[state.yDimension],
    color: groupColors[entry.group],
    hoverText: `${entry.group}<br>${buildGroupHoverText(entry)}`,
    text: entry.group,
  }));
  return placePlotLabels(items, {
    xRange: [0, 1],
    yRange: [0, 1],
    fontSize: state.fontSize,
    pointClearancePx: 16,
    plotWidth: DEFAULT_LABEL_PLOT_WIDTH,
    plotHeight: DEFAULT_LABEL_PLOT_HEIGHT,
  });
}

function placeFeatureCorrelationLabels(features, groupColors) {
  const items = features.map((feature) => ({
    anchorX: feature.plotX,
    anchorY: feature.plotY,
    color: groupColors[feature.group],
    group: feature.group,
    hoverText:
      `<b>${feature.feature_name}</b><br>` +
      `Group: ${feature.group}<br>` +
      `${state.xDimension}: ${formatValue(feature.x)}<br>` +
      `${state.yDimension}: ${formatValue(feature.y)}<br>` +
      `Plane magnitude: ${formatValue(feature.rankingScore)}`,
    text: feature.plot_feature_name,
  }));
  return placePlotLabels(items, {
    xRange: computeLabelRange([...items.map((item) => item.anchorX), 0], false),
    yRange: computeLabelRange([...items.map((item) => item.anchorY), 0], false),
    fontSize: state.fontSize,
    pointClearancePx: 14,
    plotWidth: DEFAULT_LABEL_PLOT_WIDTH,
    plotHeight: DEFAULT_LABEL_PLOT_HEIGHT,
  });
}

function placePlotLabels(items, options) {
  const placed = [];
  const pointBoxes = items.map((item) =>
    buildPlotPointBox(item.anchorX, item.anchorY, options)
  );

  items
    .slice()
    .sort((left, right) => {
      const leftMagnitude = Math.hypot(left.anchorX, left.anchorY);
      const rightMagnitude = Math.hypot(right.anchorX, right.anchorY);
      return rightMagnitude - leftMagnitude || left.text.localeCompare(right.text);
    })
    .forEach((item, index) => {
      const candidates = buildPlotLabelCandidates(item, index, options);
      const firstBox = buildPlotLabelBox(item.text, candidates[0].x, candidates[0].y, options);
      const firstLabelOverlap = placed.some((label) =>
        labelBoxOverlapArea(firstBox, label.box) > 0
      );
      let bestCandidate = candidates[0];
      let bestPenalty = Infinity;

      candidates.forEach((candidate) => {
        const box = buildPlotLabelBox(item.text, candidate.x, candidate.y, options);
        const overlapPenalty = placed.reduce(
          (penalty, label) => penalty + labelBoxOverlapArea(box, label.box),
          0
        );
        const pointPenalty = pointBoxes.reduce(
          (penalty, pointBox) => penalty + labelBoxOverlapArea(box, pointBox) * 50,
          0
        );
        const distancePenalty = Math.hypot(
          candidate.x - item.anchorX,
          candidate.y - item.anchorY
        ) * 0.01;
        const penalty = overlapPenalty + pointPenalty + distancePenalty;
        if (penalty < bestPenalty) {
          bestCandidate = { ...candidate, box, overlapPenalty };
          bestPenalty = penalty;
        }
      });

      placed.push({
        anchorX: item.anchorX,
        anchorY: item.anchorY,
        box: bestCandidate.box,
        color: item.color,
        connector: firstLabelOverlap || bestCandidate.overlapPenalty > 0,
        group: item.group,
        hoverText: item.hoverText,
        text: item.text,
        x: bestCandidate.x,
        y: bestCandidate.y,
      });
    });

  return placed;
}

function buildPlotLabelCandidates(item, itemIndex, options) {
  const xSpan = options.xRange[1] - options.xRange[0];
  const ySpan = options.yRange[1] - options.yRange[0];
  const unit = Math.max(Math.min(xSpan, ySpan), 1e-8);
  const magnitude = Math.hypot(item.anchorX, item.anchorY);
  const directionX = magnitude > 1e-8 ? item.anchorX / magnitude : 1;
  const directionY = magnitude > 1e-8 ? item.anchorY / magnitude : 0;
  const tangentX = -directionY;
  const tangentY = directionX;
  const lateralSign = itemIndex % 2 === 0 ? 1 : -1;
  const candidates = [];

  for (let ring = 0; ring <= 12; ring += 1) {
    const radialOffset = unit * (0.034 + ring * 0.024);
    const lateralOffsets = ring === 0
      ? [0]
      : [0, lateralSign * ring * unit * 0.017, -lateralSign * ring * unit * 0.017];

    lateralOffsets.forEach((lateralOffset) => {
      const x = clamp(
        item.anchorX + directionX * radialOffset + tangentX * lateralOffset,
        options.xRange[0],
        options.xRange[1]
      );
      const y = clamp(
        item.anchorY + directionY * radialOffset + tangentY * lateralOffset,
        options.yRange[0],
        options.yRange[1]
      );
      candidates.push({ x, y });
    });
  }

  return candidates;
}

function buildPlotLabelBox(text, x, y, options) {
  const xSpan = options.xRange[1] - options.xRange[0];
  const ySpan = options.yRange[1] - options.yRange[0];
  const width = ((text.length * options.fontSize * 0.58) + 12) /
    options.plotWidth * xSpan;
  const height = (options.fontSize + 8) / options.plotHeight * ySpan;

  return {
    bottom: y - height / 2,
    left: x - width / 2,
    right: x + width / 2,
    top: y + height / 2,
  };
}

function buildPlotPointBox(x, y, options) {
  const xSpan = options.xRange[1] - options.xRange[0];
  const ySpan = options.yRange[1] - options.yRange[0];
  const width = options.pointClearancePx / options.plotWidth * xSpan;
  const height = options.pointClearancePx / options.plotHeight * ySpan;

  return {
    bottom: y - height / 2,
    left: x - width / 2,
    right: x + width / 2,
    top: y + height / 2,
  };
}

function buildPlotLabelConnectorTraces(labelPlacement, traceOptions = {}) {
  return labelPlacement
    .filter((label) => label.connector)
    .map((label) => ({
      type: 'scatter',
      mode: 'lines',
      name: `${label.text} label connector`,
      x: [label.anchorX, label.x],
      y: [label.anchorY, label.y],
      line: {
        color: withAlpha(label.color, 0.65),
        width: 1,
        dash: 'dot',
      },
      hoverinfo: 'skip',
      showlegend: false,
      ...traceOptions,
    }));
}

function buildPlotLabelTrace(labelPlacement, fontSize, traceOptions = {}) {
  if (!labelPlacement.length) {
    return null;
  }

  return {
    type: 'scatter',
    mode: 'text',
    name: traceOptions.name ?? 'Labels',
    x: labelPlacement.map((label) => label.x),
    y: labelPlacement.map((label) => label.y),
    text: labelPlacement.map((label) => label.text),
    textposition: 'middle center',
    textfont: {
      color: labelPlacement.map((label) => label.color),
      size: fontSize,
      family: 'Arial, sans-serif',
    },
    hoverinfo: 'skip',
    cliponaxis: false,
    showlegend: false,
    ...traceOptions,
  };
}

function computeLabelRange(values, includeZero) {
  const finiteValues = values.filter((value) => Number.isFinite(value));
  if (includeZero) {
    finiteValues.push(0);
  }
  if (!finiteValues.length) {
    return [-1, 1];
  }

  let min = Math.min(...finiteValues);
  let max = Math.max(...finiteValues);
  if (min === max) {
    const delta = Math.max(Math.abs(min) * 0.2, 0.1);
    min -= delta;
    max += delta;
  }

  const padding = (max - min) * 0.18;
  return [min - padding, max + padding];
}

function buildGroupLayout() {
  const themeColors = getThemeColors();
  return {
    paper_bgcolor: 'rgba(0, 0, 0, 0)',
    plot_bgcolor: 'rgba(255, 255, 255, 0)',
    margin: SECONDARY_SQUARE_PLOT_MARGIN,
    showlegend: false,
    font: {
      color: themeColors.font,
      family: 'Arial, sans-serif',
      size: themeColors.fontSize,
    },
    xaxis: {
      title: {
        text: dimensionsByKey[state.xDimension].label,
        font: { color: themeColors.font, size: themeColors.fontSize },
      },
      range: [0, 1],
      fixedrange: true,
      constrain: 'domain',
      scaleanchor: 'y',
      scaleratio: 1,
      automargin: true,
      zeroline: true,
      zerolinecolor: themeColors.zeroline,
      zerolinewidth: 1,
      gridcolor: themeColors.grid,
      gridwidth: 1,
      tickfont: { color: themeColors.font, size: themeColors.fontSize },
    },
    yaxis: {
      title: {
        text: dimensionsByKey[state.yDimension].label,
        font: { color: themeColors.font, size: themeColors.fontSize },
      },
      range: [0, 1],
      fixedrange: true,
      constrain: 'domain',
      automargin: true,
      zeroline: true,
      zerolinecolor: themeColors.zeroline,
      zerolinewidth: 1,
      gridcolor: themeColors.grid,
      gridwidth: 1,
      tickfont: { color: themeColors.font, size: themeColors.fontSize },
    },
    annotations: [],
  };
}

function updateGroupSummary(groups) {
  const target = document.getElementById('group-summary-text');
  if (!target) {
    return;
  }
  if (!groups.length) {
    target.textContent = '';
    return;
  }

  target.textContent = `${groups.length} groups shown`;
}

function renderPartialAxesPlot() {
  const themeColors = getThemeColors();
  const partialAxes = (payload.partial_correlations ?? []).filter(
    (entry) => entry.partial_axis === 1 || entry.partial_axis === 2
  );
  const seriesKeys = [...new Set(partialAxes.map((entry) => `${entry.group}::${entry.partial_axis}`))];
  const groupColors = getGroupColorMap();

  const vectorSeries = seriesKeys.map((seriesKey) => {
    const [group, partialAxisText] = seriesKey.split('::');
    const partialAxis = Number(partialAxisText);
    const seriesEntries = partialAxes.filter(
      (entry) => entry.group === group && entry.partial_axis === partialAxis
    );
    const vector = buildPartialAxesVector(seriesEntries);
    if (!vector) {
      return null;
    }

    const label = `Dim ${partialAxis} ${group}`;
    const color = groupColors[group];

    return {
      color,
      hoverText: seriesEntries
        .map(
          (entry) =>
            `${entry.group}<br>Partial axis ${entry.partial_axis}<br>${entry.global_dim}: ${formatValue(entry.value)}`
        )
        .join('<br>'),
      label,
      seriesKey,
      vector,
    };
  }).filter(Boolean);
  const labelPlacement = placePartialAxesLabels(vectorSeries);
  const traces = vectorSeries.flatMap((series) => [
    buildPartialAxesVectorTrace(series, themeColors),
  ]);
  traces.push(...buildPlotLabelConnectorTraces(labelPlacement));
  const labelTrace = buildPlotLabelTrace(labelPlacement, state.fontSize);
  if (labelTrace) {
    traces.push(labelTrace);
  }

  traces.unshift(buildPartialAxesCircleBoundary());

  Plotly.react(
    'partial-axes-plot',
    traces,
    buildPartialAxesLayout(),
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

function buildPartialAxesVectorTrace(series, themeColors) {
  return {
    type: 'scatter',
    mode: 'lines+markers',
    name: series.label,
    legendgroup: `axes:${series.seriesKey}`,
    x: [0, series.vector.x],
    y: [0, series.vector.y],
    customdata: ['', series.hoverText],
    hovertemplate: '%{customdata}<extra></extra>',
    marker: {
      color: series.color,
      size: [0, 9],
      symbol: 'circle',
      line: {
        color: themeColors.markerLine,
        width: 1,
      },
    },
    line: {
      color: withAlpha(series.color, 0.7),
      width: 2,
    },
  };
}

function placePartialAxesLabels(vectorSeries) {
  const items = vectorSeries.map((series) => ({
    anchorX: series.vector.x,
    anchorY: series.vector.y,
    color: series.color,
    hoverText: series.hoverText,
    text: series.label,
  }));
  return placePlotLabels(items, {
    xRange: [PARTIAL_AXES_X_RANGE[0] + 0.04, PARTIAL_AXES_X_RANGE[1] - 0.04],
    yRange: [PARTIAL_AXES_Y_RANGE[0] + 0.04, PARTIAL_AXES_Y_RANGE[1] - 0.04],
    fontSize: state.fontSize,
    pointClearancePx: 14,
    plotWidth: 520,
    plotHeight: 460,
  });
}

function labelBoxOverlapArea(left, right) {
  const width = Math.max(0, Math.min(left.right, right.right) - Math.max(left.left, right.left));
  const height = Math.max(0, Math.min(left.top, right.top) - Math.max(left.bottom, right.bottom));
  return width * height;
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
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

function buildPartialAxesLayout() {
  const themeColors = getThemeColors();
  return {
    paper_bgcolor: 'rgba(0, 0, 0, 0)',
    plot_bgcolor: 'rgba(255, 255, 255, 0)',
    margin: SECONDARY_SQUARE_PLOT_MARGIN,
    font: {
      color: themeColors.font,
      family: 'Arial, sans-serif',
      size: themeColors.fontSize,
    },
    showlegend: false,
    xaxis: {
      title: {
        text: dimensionsByKey[state.xDimension].label,
        font: { color: themeColors.font, size: themeColors.fontSize },
      },
      range: PARTIAL_AXES_X_RANGE,
      constrain: 'domain',
      scaleanchor: 'y',
      scaleratio: 1,
      automargin: true,
      gridcolor: themeColors.grid,
      gridwidth: 1,
      zeroline: true,
      zerolinecolor: themeColors.zeroline,
      zerolinewidth: 1,
      tickfont: { color: themeColors.font, size: themeColors.fontSize },
    },
    yaxis: {
      title: {
        text: dimensionsByKey[state.yDimension].label,
        font: { color: themeColors.font, size: themeColors.fontSize },
      },
      range: PARTIAL_AXES_Y_RANGE,
      constrain: 'domain',
      automargin: true,
      gridcolor: themeColors.grid,
      gridwidth: 1,
      zeroline: true,
      zerolinecolor: themeColors.zeroline,
      zerolinewidth: 1,
      tickfont: { color: themeColors.font, size: themeColors.fontSize },
    },
    annotations: [],
  };
}

function updatePartialAxesSummary(partialAxes) {
  const target = document.getElementById('partial-axes-summary');
  if (!target) {
    return;
  }
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

  const barTrace = {
    type: 'bar',
    name: 'Explained variance',
    x: components.map((component) => component.label),
    y: components.map((component) => component.variance_explained),
    marker: {
      color: components.map((component) =>
        selectedDimensions.has(component.key)
          ? SELECTED_DIMENSION_COLOR
          : VARIANCE_MARKER_COLOR
      ),
      line: {
        color: themeColors.markerLine,
        width: 1,
      },
    },
    customdata: components.map((component) => [component.variance_explained]),
    hovertemplate: '%{x}: %{customdata[0]:.2f}% explained<extra></extra>',
  };

  Plotly.react(
    'variance-plot',
    [barTrace],
    buildVarianceLayout(),
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

  renderCumulativeVariancePlot(components, themeColors);
  updateVarianceSummary(components);
}

function renderCumulativeVariancePlot(components, themeColors) {
  let cumulativeTotal = 0;
  const selectedDimensions = new Set([state.xDimension, state.yDimension]);
  const cumulativeTrace = {
    type: 'scatter',
    mode: 'lines+markers',
    name: 'Cumulative explained variance',
    x: components.map((component) => component.label),
    y: components.map((component) => {
      cumulativeTotal += component.variance_explained;
      return cumulativeTotal;
    }),
    line: {
      color: VARIANCE_MARKER_COLOR,
      width: 3,
    },
    marker: {
      color: components.map((component) =>
        selectedDimensions.has(component.key)
          ? SELECTED_DIMENSION_COLOR
          : VARIANCE_MARKER_COLOR
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
    [cumulativeTrace],
    buildCumulativeVarianceLayout(),
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

function buildVarianceLayout() {
  const themeColors = getThemeColors();
  return {
    paper_bgcolor: 'rgba(0, 0, 0, 0)',
    plot_bgcolor: 'rgba(255, 255, 255, 0)',
    margin: VARIANCE_PLOT_MARGIN,
    font: {
      color: themeColors.font,
      family: 'Arial, sans-serif',
      size: themeColors.fontSize,
    },
    bargap: 0.24,
    xaxis: {
      tickfont: { color: themeColors.font, size: themeColors.fontSize },
    },
    yaxis: {
      title: {
        text: 'Explained variance (%)',
        font: { color: themeColors.font, size: themeColors.fontSize },
      },
      rangemode: 'tozero',
      gridcolor: themeColors.grid,
      gridwidth: 1,
      tickfont: { color: themeColors.font, size: themeColors.fontSize },
    },
    annotations: [],
  };
}

function buildCumulativeVarianceLayout() {
  const themeColors = getThemeColors();
  return {
    paper_bgcolor: 'rgba(0, 0, 0, 0)',
    plot_bgcolor: 'rgba(255, 255, 255, 0)',
    margin: CUMULATIVE_VARIANCE_PLOT_MARGIN,
    font: {
      color: themeColors.font,
      family: 'Arial, sans-serif',
      size: themeColors.fontSize,
    },
    xaxis: {
      showgrid: true,
      gridcolor: themeColors.gridSoft,
      gridwidth: 1,
      tickfont: { color: themeColors.font, size: themeColors.fontSize },
    },
    yaxis: {
      title: {
        text: 'Cumulative explained variance (%)',
        font: { color: themeColors.font, size: themeColors.fontSize },
      },
      range: [0, 104],
      gridcolor: themeColors.grid,
      gridwidth: 1,
      tickfont: { color: themeColors.font, size: themeColors.fontSize },
      zeroline: true,
    },
    annotations: [],
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
    fontSize: state.fontSize,
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

function updateVarianceSummary(components) {
  const totalExplained = components.reduce(
    (sum, component) => sum + component.variance_explained,
    0
  );
  document.getElementById('variance-summary').textContent =
    `${formatValue(totalExplained)}% across ${components.length} components`;
}

function updateCumulativeSummary(components) {
  const finalValue = components.reduce(
    (sum, component) => sum + component.variance_explained,
    0
  );
  document.getElementById('cumulative-summary').textContent =
    `${formatValue(finalValue)}% at component ${components.length}`;
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
