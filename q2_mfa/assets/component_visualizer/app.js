// ============================================================================
// CONSTANTS & CONFIGURATION
// ============================================================================

const COLOR_PALETTES = {
  Plotly: {
    kind: 'categorical',
    colors: ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880'],
  },
  'Colorblind Safe': {
    kind: 'categorical',
    colors: ['#E69F00', '#56B4E9', '#009E73', '#F0E442', '#0072B2', '#D55E00', '#CC79A7', '#000000'],
  },
  Tableau: {
    kind: 'categorical',
    colors: ['#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F', '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC'],
  },
  Dark2: {
    kind: 'categorical',
    colors: ['#1B9E77', '#D95F02', '#7570B3', '#E7298A', '#66A61E', '#E6AB02', '#A6761D', '#666666'],
  },
  Set2: {
    kind: 'categorical',
    colors: ['#66C2A5', '#FC8D62', '#8DA0CB', '#E78AC3', '#A6D854', '#FFD92F', '#E5C494', '#B3B3B3'],
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

const SCIENTIFIC_FONTS = [
  { label: 'Arial', family: 'Arial, sans-serif' },
  { label: 'Helvetica', family: 'Helvetica, Arial, sans-serif' },
  { label: 'Times New Roman', family: '"Times New Roman", Times, serif' },
  { label: 'Georgia', family: 'Georgia, serif' },
  { label: 'Garamond', family: 'Garamond, "Times New Roman", serif' },
  { label: 'Palatino', family: '"Palatino Linotype", Palatino, serif' },
  { label: 'Cambria', family: 'Cambria, Georgia, serif' },
  { label: 'Calibri', family: 'Calibri, Arial, sans-serif' },
  { label: 'Verdana', family: 'Verdana, Arial, sans-serif' },
  { label: 'Computer Modern', family: '"Computer Modern", "Latin Modern Roman", "Times New Roman", serif' },
];

const MISSING_VALUE_TOKEN = '__MISSING__';
// Shared Plotly hover template: every point trace renders a pre-built HTML
// string supplied via customdata, so all plots hover identically.
const HOVER_TEMPLATE = '%{customdata}<extra></extra>';
const DEFAULT_MARKER_COLOR = '#6B7280';
const VARIANCE_MARKER_COLOR = '#126782';
const SELECTED_DIMENSION_COLOR = '#083D5B';
const ELLIPSE_SCALE = 2.4477;
const PARTIAL_AXES_X_RANGE = [-1.08, 1.3];
const PARTIAL_AXES_Y_RANGE = [-1.19, 1.19];
const DEFAULT_LABEL_PLOT_WIDTH = 560;
const DEFAULT_LABEL_PLOT_HEIGHT = 420;
const MAX_FEATURE_OVERLAY_COUNT = 100;
// Tables selectable in the data-table dropdown. `field` is the per-component
// value read from each record; `aggregate`, when present, is how the last column
// combines the two displayed dimensions ('magnitude' = sqrt(x^2 + y^2),
// 'sum' = x + y).
const TABLE_SOURCES = {
  'component-summary': { label: 'Eigenvalues and variance', entity: 'dimension', recordSet: 'dimensions' },
  'sample-coordinates': { label: 'Sample coordinates', entity: 'sample', recordSet: 'samples', field: 'coordinate', valueLabel: 'coordinate', aggregate: 'magnitude', aggregateLabel: 'Plane magnitude' },
  'sample-contributions': { label: 'Sample contributions', entity: 'sample', recordSet: 'samples', field: 'contribution', valueLabel: 'contribution', format: 'fractionPercent' },
  'sample-cos2': { label: 'Sample cos2', entity: 'sample', recordSet: 'samples', field: 'cos2', valueLabel: 'cos2', aggregate: 'sum', aggregateLabel: 'Sum' },
  'feature-coordinates': { label: 'Feature coordinates', entity: 'feature', recordSet: 'features', field: 'coordinate', valueLabel: 'coordinate', aggregate: 'magnitude', aggregateLabel: 'Plane magnitude' },
  'feature-correlations': { label: 'Feature correlations', entity: 'feature', recordSet: 'features', field: 'correlation', valueLabel: 'correlation', aggregate: 'magnitude', aggregateLabel: 'Plane magnitude' },
  'feature-contributions': { label: 'Feature contributions', entity: 'feature', recordSet: 'features', field: 'contribution', valueLabel: 'contribution', format: 'fractionPercent' },
  'feature-cos2': { label: 'Feature cos2', entity: 'feature', recordSet: 'features', field: 'cos2', valueLabel: 'cos2', aggregate: 'sum', aggregateLabel: 'Sum' },
  'group-coordinates': { label: 'Group coordinates', entity: 'group', recordSet: 'groups', field: 'coordinate', valueLabel: 'coordinate', aggregate: 'magnitude', aggregateLabel: 'Plane magnitude', mfaOnly: true },
  'group-contributions': { label: 'Group contributions', entity: 'group', recordSet: 'groups', field: 'contribution', valueLabel: 'contribution', format: 'fractionPercent', mfaOnly: true },
  'group-cos2': { label: 'Group cos2', entity: 'group', recordSet: 'groups', field: 'cos2', valueLabel: 'cos2', aggregate: 'sum', aggregateLabel: 'Sum', mfaOnly: true },
  'partial-sample-coordinates': { label: 'Partial sample coordinates', entity: 'partial_sample', recordSet: 'partial_samples', field: 'coordinate', valueLabel: 'coordinate', aggregate: 'magnitude', aggregateLabel: 'Plane magnitude', mfaOnly: true },
  'partial-correlations': { label: 'Partial correlations', entity: 'partial_axis', recordSet: 'partial_axes', field: 'correlation', valueLabel: 'correlation', aggregate: 'magnitude', aggregateLabel: 'Plane magnitude', mfaOnly: true },
  'partial-contributions': { label: 'Partial contributions', entity: 'partial_axis', recordSet: 'partial_axes', field: 'contribution', valueLabel: 'contribution', format: 'fractionPercent', mfaOnly: true },
};
const SAMPLE_LEGEND_MIN_RIGHT_MARGIN = 150;
const SAMPLE_LEGEND_MAX_RIGHT_MARGIN = 420;
const SAMPLE_LEGEND_SYMBOL_WIDTH = 46;
const SAMPLE_LEGEND_LABEL_PADDING = 34;
const SAMPLE_LEGEND_CHARACTER_WIDTH = 7.2;
const SAMPLE_NUMERIC_COLORBAR_Y = 1;
const SAMPLE_NUMERIC_COLORBAR_LENGTH = 0.28;
const SAMPLE_LEGEND_BELOW_COLORBAR_Y = 0.72;
const FEATURE_SCALE_CIRCLE_COLOR = 'rgba(148, 163, 184, 0.72)';
const SECONDARY_SQUARE_PLOT_MARGIN = { t: 20, r: 46, b: 70, l: 80 };
const VARIANCE_PLOT_MARGIN = { t: 20, r: 20, b: 42, l: 80 };
const CUMULATIVE_VARIANCE_PLOT_MARGIN = { t: 28, r: 56, b: 42, l: 80 };

// ============================================================================
// DATA & APPLICATION STATE
// ============================================================================

const payload = window.COMPONENT_VISUALIZER_DATA;
const analysisType = payload.analysis_type ?? 'mfa';
const analysisLabel = analysisType.toUpperCase();
const isMfa = analysisType === 'mfa';
const metadataColumns = payload.metadata_columns ?? [];
const hasMetadata = metadataColumns.length > 0;
const metadataByName = Object.fromEntries(
  metadataColumns.map((column) => [column.name, column])
);
const dimensionsByKey = Object.fromEntries(
  payload.dimensions.map((dimension) => [Number(dimension.component), dimension])
);
const featureSources = {
  coordinates: {
    records: payload.features ?? [],
    valueKey: 'coordinate',
  },
  correlations: {
    records: payload.features ?? [],
    valueKey: 'correlation',
  },
};
const samples = payload.samples ?? [];
const partialSamples = payload.partial_samples ?? [];
const groupSummary = payload.groups ?? [];
const groupNames = groupSummary.map((entry) => entry.group);
// Highest number of partial axes any group exposes (partial_component is
// 0-based), used to bound the "partial axes per group" control.
const maxPartialAxisCount = (payload.partial_axes ?? []).reduce(
  (max, entry) => Math.max(max, entry.partial_component + 1),
  1
);
const DEFAULT_PARTIAL_AXIS_COUNT = Math.min(2, maxPartialAxisCount);
const samplesById = Object.fromEntries(
  samples.map((sample) => [sample.sample_id, sample])
);
const state = {
  // Prince always returns components in order, so the first two dimensions (0
  // and 1) are the default axes.
  xDimension: 0,
  yDimension: 1,
  colorBy: '',
  sizeBy: '',
  colorPalette: 'Plotly',
  showSampleScores: true,
  showBarycenter: false,
  showPartialOverlay: false,
  showFeatures: false,
  showFeatureScaleCircle: false,
  featureSource: 'coordinates',
  showFullFeatureLabels: false,
  topFeatureCount: 10,
  partialAxisCount: DEFAULT_PARTIAL_AXIS_COUNT,
  featureScale: 1,
  pointSizeScale: 1,
  pointOpacity: 0.9,
  showPointBorder: true,
  selectedSampleId: null,
  tableSource: 'feature-coordinates',
  featureTableSort: {
    column: 'aggregate',
    direction: 'desc',
  },
  featureGroups: new Set(groupNames),
  partialSampleGroups: new Set(groupNames),
  fontFamily: SCIENTIFIC_FONTS[0].family,
  fontSize: 12,
  filters: [],
};

// ============================================================================
// DATA ACCESSORS
// ============================================================================

// The payload is columnar: each entity stores per-field arrays indexed by
// component id, so a value read is an O(1) array index rather than a scan.
function componentField(entry, component, field) {
  return entry[field]?.[Number(component)];
}

function sampleValue(sample, component) {
  return componentField(sample, component, 'coordinate');
}

function partialSampleValue(entry, component) {
  return componentField(entry, component, 'coordinate');
}

function featureValue(feature, source, component) {
  return componentField(feature, component, source.valueKey);
}

function groupCoordinateValue(entry, component) {
  return componentField(entry, component, 'coordinate');
}

function groupContributionValue(entry, component) {
  return componentField(entry, component, 'contribution');
}

function groupCos2Value(entry, component) {
  return componentField(entry, component, 'cos2');
}

function dimensionLabel(component) {
  return dimensionsByKey[component]?.label ?? `Dim ${Number(component) + 1}`;
}

function dimensionAxisTitle(component) {
  return dimensionsByKey[component]?.axis_title ?? dimensionLabel(component);
}

function dimensionFileLabel(component) {
  return dimensionLabel(component).toLowerCase().replace(/\s+/g, '-');
}

function createDefaultSampleFilter() {
  return {
    field: '',
    categoricalValues: new Set(),
    numericMin: null,
    numericMax: null,
  };
}

// ============================================================================
// INITIALIZATION & CONTROL POPULATION
// ============================================================================

function initialize() {
  applyAnalysisLabels();
  applyAnalysisMode();
  applyMetadataAvailability();
  populateDimensionSelectors();
  populateColorControls();
  bindEvents();
  bindSamplePlotResizeObserver();
  renderFilterControls();
  renderAll();
}

function applyAnalysisLabels() {
  document.title = analysisLabel;
  const eyebrow = document.getElementById('analysis-eyebrow');
  if (eyebrow) {
    eyebrow.textContent = analysisLabel;
  }
}

function applyAnalysisMode() {
  document.querySelectorAll('.mfa-only').forEach((element) => {
    element.hidden = !isMfa;
  });
}

function applyMetadataAvailability() {
  document
    .querySelector('.sample-plot-layout')
    ?.classList.toggle('sample-plot-layout-no-metadata', !hasMetadata);

  [
    '.sample-details-panel',
    '.control-group-color-by',
    '.control-group-color-palette',
    '.control-group-size-by',
  ].forEach((selector) => {
    const element = document.querySelector(selector);
    if (element) {
      element.hidden = !hasMetadata;
    }
  });
}

function bindSamplePlotResizeObserver() {
  const samplePlotLayout = document.querySelector('.sample-plot-layout');
  if (!samplePlotLayout || !window.ResizeObserver) {
    return;
  }

  let resizeAnimationFrame = null;
  const resizeObserver = new ResizeObserver(() => {
    if (resizeAnimationFrame !== null) {
      window.cancelAnimationFrame(resizeAnimationFrame);
    }

    resizeAnimationFrame = window.requestAnimationFrame(() => {
      renderSamplePlot();
      resizeAnimationFrame = null;
    });
  });
  resizeObserver.observe(samplePlotLayout);
}

function populateDimensionSelectors() {
  const xDimension = document.getElementById('x-dimension');
  const yDimension = document.getElementById('y-dimension');

  payload.dimensions.forEach((dimension) => {
    const xOption = new Option(dimension.label, dimension.component);
    const yOption = new Option(dimension.label, dimension.component);
    xDimension.add(xOption);
    yDimension.add(yOption);
  });

  xDimension.value = String(state.xDimension);
  yDimension.value = String(state.yDimension);
}

function populateColorControls() {
  const colorBy = document.getElementById('color-by');
  colorBy.add(new Option('None', ''));
  metadataColumns.forEach((column) => {
    colorBy.add(new Option(column.name, column.name));
  });

  const sizeBy = document.getElementById('size-by');
  sizeBy.add(new Option('None', ''));
  metadataColumns
    .filter((column) => column.type === 'numeric')
    .forEach((column) => {
      sizeBy.add(new Option(column.name, column.name));
    });

  const fontFamily = document.getElementById('font-family');
  SCIENTIFIC_FONTS.forEach((font) => {
    fontFamily.add(new Option(font.label, font.family));
  });

  const tableSource = document.getElementById('table-source');
  Object.entries(TABLE_SOURCES).forEach(([key, source]) => {
    if (isTableSourceAvailable(source)) {
      tableSource.add(new Option(source.label, key));
    }
  });
  if (!isTableSourceAvailable(TABLE_SOURCES[state.tableSource])) {
    state.tableSource = tableSource.options[0]?.value ?? state.tableSource;
  }
  tableSource.value = state.tableSource;

  repopulateColorPaletteOptions();
  sizeBy.value = state.sizeBy;
  document.getElementById('show-barycenter').checked = state.showBarycenter;
  document.getElementById('show-sample-coordinates').checked = state.showSampleScores;
  document.getElementById('show-full-feature-labels').checked = state.showFullFeatureLabels;
  document.getElementById('show-feature-scale-circle').checked = state.showFeatureScaleCircle;
  document.getElementById('top-feature-count').value = state.topFeatureCount;
  const partialAxesCount = document.getElementById('partial-axes-count');
  partialAxesCount.max = maxPartialAxisCount;
  partialAxesCount.value = state.partialAxisCount;
  document.getElementById('feature-scale').value = state.featureScale;
  document.getElementById('point-size-scale').value = state.pointSizeScale;
  document.getElementById('point-opacity').value = state.pointOpacity;
  document.getElementById('show-point-border').checked = state.showPointBorder;
  fontFamily.value = state.fontFamily;
  document.getElementById('font-size').value = state.fontSize;
}

// ============================================================================
// EVENT BINDINGS
// ============================================================================

// Each binding names the render scope it needs; anything unspecified only
// affects the main sample plot (renderSamplePlot).
const SELECT_BINDINGS = [
  { id: 'x-dimension', key: 'xDimension', transform: Number, render: renderAll },
  { id: 'y-dimension', key: 'yDimension', transform: Number, render: renderAll },
  { id: 'size-by', key: 'sizeBy' },
  { id: 'color-palette', key: 'colorPalette' },
  { id: 'font-family', key: 'fontFamily', render: renderPlots },
];

const CHECKBOX_BINDINGS = [
  { id: 'show-sample-coordinates', key: 'showSampleScores' },
  { id: 'show-barycenter', key: 'showBarycenter' },
  { id: 'show-full-feature-labels', key: 'showFullFeatureLabels' },
  { id: 'show-feature-scale-circle', key: 'showFeatureScaleCircle' },
  { id: 'show-point-border', key: 'showPointBorder' },
];

// Numeric inputs with an optional integer transform, a lower bound (below which
// the edit is ignored), and an optional upper clamp.
const NUMERIC_INPUT_BINDINGS = [
  { id: 'top-feature-count', key: 'topFeatureCount', min: 1, max: MAX_FEATURE_OVERLAY_COUNT, transform: Math.floor },
  { id: 'partial-axes-count', key: 'partialAxisCount', min: 1, max: maxPartialAxisCount, transform: Math.floor, render: renderPartialAxesPlot },
  { id: 'feature-scale', key: 'featureScale', min: 1, transform: Math.floor },
  { id: 'point-size-scale', key: 'pointSizeScale', min: 0.5, max: 1.5 },
  { id: 'point-opacity', key: 'pointOpacity', min: 0.1, max: 1 },
  { id: 'font-size', key: 'fontSize', min: 8, max: 24, transform: Math.round, render: renderPlots },
];

function bindSelect({ id, key, transform, render = renderSamplePlot }) {
  document.getElementById(id).addEventListener('change', (event) => {
    state[key] = transform ? transform(event.target.value) : event.target.value;
    render();
  });
}

function bindCheckbox({ id, key, render = renderSamplePlot }) {
  document.getElementById(id).addEventListener('change', (event) => {
    state[key] = event.target.checked;
    render();
  });
}

function bindNumericInput({ id, key, min, max, transform, render = renderSamplePlot }) {
  document.getElementById(id).addEventListener('input', (event) => {
    let nextValue = Number(event.target.value);
    if (transform) {
      nextValue = transform(nextValue);
    }
    if (!Number.isFinite(nextValue) || nextValue < min) {
      return;
    }
    if (max !== undefined) {
      nextValue = Math.min(nextValue, max);
    }
    state[key] = nextValue;
    event.target.value = nextValue;
    render();
  });
}

function bindEvents() {
  SELECT_BINDINGS.forEach(bindSelect);
  CHECKBOX_BINDINGS.forEach(bindCheckbox);
  NUMERIC_INPUT_BINDINGS.forEach(bindNumericInput);

  // color-by is special: it also re-derives the available palette options.
  document.getElementById('color-by').addEventListener('change', (event) => {
    state.colorBy = event.target.value;
    repopulateColorPaletteOptions();
    renderSamplePlot();
  });

  document.getElementById('table-source').addEventListener('change', (event) => {
    state.tableSource = event.target.value;
    // Reset so we never keep a sort column that the newly selected table
    // doesn't have.
    state.featureTableSort = getDefaultTableSort();
    renderDataTable();
  });

  // The header is rebuilt per render, so delegate sort clicks to the thead.
  document.getElementById('feature-table-head').addEventListener('click', (event) => {
    const button = event.target.closest('[data-feature-sort]');
    if (!button) {
      return;
    }
    updateFeatureTableSort(button);
    renderDataTable();
  });

  document.getElementById('download-feature-table').addEventListener('click', () => {
    downloadFeatureTableTsv();
  });
}

// ============================================================================
// FILTER CONTROLS (UI CONSTRUCTION)
// ============================================================================

function renderFilterControls() {
  const container = document.getElementById('filter-controls');
  container.replaceChildren();

  container.appendChild(buildFeaturesRow());
  if (isMfa) {
    container.appendChild(buildPartialCoordinatesRow());
  }

  if (!hasMetadata) {
    return;
  }

  state.filters.forEach((filter, index) => {
    container.appendChild(buildSampleFilterRow(filter, index));
  });

  const addRow = document.createElement('div');
  addRow.className = 'filter-row';

  const addButton = document.createElement('button');
  addButton.className = 'filter-add';
  addButton.type = 'button';
  addButton.textContent = 'Add metadata filter';
  addButton.style.gridColumn = '1';
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

function buildFeatureSourceToggle() {
  const container = document.createElement('div');
  container.className = 'toggle-option toggle-option-with-select';

  const input = document.createElement('input');
  input.type = 'checkbox';
  input.checked = state.showFeatures;
  input.addEventListener('change', (event) => {
    state.showFeatures = event.target.checked;
    if (state.showFeatures) state.featureGroups = new Set(getFeatureGroups());
    renderFilterControls();
    renderSamplePlot();
  });

  const select = document.createElement('select');
  select.setAttribute('aria-label', 'Feature source');
  select.add(new Option('Feature coord.', 'coordinates'));
  select.add(new Option('Feature corr.', 'correlations'));
  select.value = state.featureSource;
  select.addEventListener('click', (event) => {
    event.stopPropagation();
  });
  select.addEventListener('change', (event) => {
    event.stopPropagation();
    state.featureSource = event.target.value;
    state.featureGroups = new Set(getFeatureGroups());
    renderFilterControls();
    renderSamplePlot();
  });

  const help = document.createElement('span');
  help.className = 'help-tooltip';
  help.tabIndex = 0;
  help.setAttribute('role', 'button');
  help.setAttribute('aria-label', 'Features help');
  help.setAttribute(
    'data-tooltip',
    'Overlays the strongest features from the selected source for the selected axes. Features are ordered by plane magnitude, calculated as sqrt(x^2 + y^2) from the selected X and Y values. Feature coordinates and correlations come from the component-analysis JSONL result tables. The checkbox controls whether features are drawn.'
  );
  help.textContent = '?';

  container.appendChild(input);
  container.appendChild(select);
  container.appendChild(help);

  return container;
}

function buildGroupTogglesContainer(selectedGroups, disabled, groups = groupNames) {
  const container = document.createElement('div');
  container.className = 'filter-options';
  groups.forEach((group) => {
    container.appendChild(
      buildCheckboxFilterOption(group, group, selectedGroups.has(group), selectedGroups, disabled)
    );
  });
  return container;
}

function buildFeaturesRow() {
  const row = document.createElement('div');
  row.className = 'filter-row filter-row-coordinate-control';

  const toggle = buildFeatureSourceToggle();
  toggle.style.gridColumn = '1';
  row.appendChild(toggle);

  if (isMfa) {
    const groups = buildGroupTogglesContainer(
      state.featureGroups,
      !state.showFeatures,
      getFeatureGroups()
    );
    groups.style.gridColumn = '2 / -1';
    row.appendChild(groups);
  }

  return row;
}

function buildPartialCoordinatesRow() {
  const row = document.createElement('div');
  row.className = 'filter-row filter-row-coordinate-control';

  const toggle = buildOverlayToggle(
    'Partial coordinates',
    state.showPartialOverlay,
    (checked) => {
      state.showPartialOverlay = checked;
      if (checked) state.partialSampleGroups = new Set(groupNames);
      renderFilterControls();
      renderSamplePlot();
    },
    "Shows each sample's group-specific partial coordinates from the MFA partial sample coordinate result table and connects them to the global sample scores. Long connectors indicate that a group places that sample away from the consensus position."
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
  const isNumeric = filter.field && metadataByName[filter.field]?.type === 'numeric';

  // Col 1: metadata field selector.
  const fieldSelect = buildSampleMetadataSelect(filter);
  fieldSelect.style.gridColumn = '1';
  row.appendChild(fieldSelect);

  // Cols 2+: numeric min/max cells or categorical value checkboxes.
  if (isNumeric) {
    appendNumericFilterCells(row, filter);
  } else {
    const valueControls = buildFilterValueControls(filter);
    valueControls.style.gridColumn = '2 / 5';
    row.appendChild(valueControls);
  }

  const removeButton = buildFilterRemoveButton(index);
  removeButton.style.gridColumn = isNumeric ? '4' : '5';
  row.appendChild(removeButton);

  return row;
}

function appendNumericFilterCells(row, filter) {
  const column = metadataByName[filter.field];
  if (filter.numericMin === null) {
    filter.numericMin = column.min;
    filter.numericMax = column.max;
  }

  const minCell = buildNumericFilterCell('Min:', filter.numericMin, (v) => {
    filter.numericMin = v;
    renderSamplePlot();
  });
  minCell.style.gridColumn = '2';
  row.appendChild(minCell);

  const maxCell = buildNumericFilterCell('Max:', filter.numericMax, (v) => {
    filter.numericMax = v;
    renderSamplePlot();
  });
  maxCell.style.gridColumn = '3';
  row.appendChild(maxCell);
}

function buildSampleMetadataSelect(filter) {
  const select = document.createElement('select');
  select.add(new Option('Select metadata…', ''));
  metadataColumns.forEach((column) => {
    select.add(new Option(column.name, column.name));
  });
  select.value = filter.field;
  select.addEventListener('change', (event) => {
    filter.field = event.target.value;
    filter.categoricalValues = new Set();
    filter.numericMin = null;
    filter.numericMax = null;
    renderFilterControls();
    renderSamplePlot();
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
    renderSamplePlot();
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
      renderSamplePlot();
    });
  }

  const text = document.createElement('span');
  text.textContent = label;

  wrapper.appendChild(checkbox);
  wrapper.appendChild(text);
  return wrapper;
}


// ============================================================================
// SAMPLE FILTERING
// ============================================================================

function getFilteredSamples() {
  return samples.filter((sample) =>
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

// ============================================================================
// RENDER ORCHESTRATION & IMAGE EXPORT
// ============================================================================

// Tracks whether the plotly_click listener is attached. It
// live on the graph div and survive Plotly.react, so they only need binding once.
let samplePlotClickBound = false;

// Render scopes. Most controls only affect the main sample plot, so they call
// renderSamplePlot() and leave the secondary plots and data table untouched.
// Only the X/Y dimension (and fonts) affect everything.
function renderSamplePlot() {
  const filteredSamples = getFilteredSamples();
  const traces = buildTraces(filteredSamples);
  const layout = buildLayout(traces);
  applySamplePlotSquareDataArea(layout);

  Plotly.react('sample-plot', traces, layout, {
    responsive: true,
    displaylogo: false,
    scrollZoom: true,
    modeBarButtonsToAdd: [
      buildImageDownloadButton('Download PNG', 'sample-plot', buildDownloadFilename('png'), 'png'),
      buildImageDownloadButton('Download SVG', 'sample-plot', buildDownloadFilename('svg'), 'svg'),
    ],
    modeBarButtonsToRemove: ['zoom2d', 'toImage', 'toImage2d', 'resetScale2d', 'lasso2d', 'select2d'],
  });

  bindSamplePlotClickEvents();
  renderSampleDetailsPanel();
}

// Toggle the fixed details panel when clicking sample points. Feature/partial
// points keep their native tooltips; their customdata is not a sample id, so the
// samplesById lookup misses and selection is unchanged for them.
function bindSamplePlotClickEvents() {
  if (samplePlotClickBound) {
    return;
  }

  const graphDiv = document.getElementById('sample-plot');
  if (!graphDiv || typeof graphDiv.on !== 'function') {
    return;
  }

  graphDiv.on('plotly_click', (data) => {
    const point = data.points?.[0];
    const sample = point ? samplesById[point.customdata] : null;
    if (!sample) {
      return;
    }
    toggleSelectedSample(sample.sample_id);
  });
  samplePlotClickBound = true;
}

function toggleSelectedSample(sampleId, { scrollToPlot = false } = {}) {
  state.selectedSampleId = state.selectedSampleId === sampleId ? null : sampleId;
  renderSampleDetailsPanel();
  updateSampleSelectionMarkerLines();
  if (scrollToPlot) {
    scrollToSamplePlot();
  }
}

function scrollToSamplePlot() {
  document.querySelector('.sample-plot-layout')?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  });
}

function updateSampleSelectionMarkerLines() {
  const graphDiv = document.getElementById('sample-plot');
  if (!graphDiv?.data) {
    return;
  }

  graphDiv.data.forEach((trace, traceIndex) => {
    const traceSampleIds = getTraceSampleIds(trace);
    if (!traceSampleIds.length) {
      return;
    }
    const traceSamples = traceSampleIds.map((sampleId) => samplesById[sampleId]);
    Plotly.restyle(
      graphDiv,
      {
        'marker.line': [
          buildSamplePointMarkerLine(
            traceSamples,
            getThemeColors().markerLine,
            1
          ),
        ],
      },
      [traceIndex]
    );
  });
}

function getTraceSampleIds(trace) {
  if (!Array.isArray(trace?.customdata)) {
    return [];
  }

  const sampleIds = trace.customdata.filter((value) => samplesById[value]);
  return sampleIds.length === trace.customdata.length ? sampleIds : [];
}

function renderSecondaryPlots() {
  if (isMfa) {
    renderGroupPlot();
    renderPartialAxesPlot();
  }
  renderVariancePlot();
}

// Every plot but not the data table (used by font changes).
function renderPlots() {
  renderSamplePlot();
  renderSecondaryPlots();
}

// Everything (used by X/Y dimension changes and initial load).
function renderAll() {
  renderSamplePlot();
  renderSecondaryPlots();
  renderDataTable();
}

function buildDownloadFilename(extension) {
  const xLabel = dimensionFileLabel(state.xDimension);
  const yLabel = dimensionFileLabel(state.yDimension);
  return `${analysisType}-sample-scores-${xLabel}-vs-${yLabel}.${extension}`;
}

function downloadPlotImage(plotId, filename, format) {
  const dimensions = getRenderedPlotDimensions(plotId);
  Plotly.downloadImage(plotId, {
    format,
    filename: filename.replace(`.${format}`, ''),
    width: dimensions.width,
    height: dimensions.height,
    scale: 2,
  });
}

function getRenderedPlotDimensions(plotId) {
  const plot = document.getElementById(plotId);
  const width = Math.round(
    plot?._fullLayout?.width ?? plot?.getBoundingClientRect().width ?? 1400
  );
  const height = Math.round(
    plot?._fullLayout?.height ?? plot?.getBoundingClientRect().height ?? 900
  );

  return {
    width: Math.max(width, 1),
    height: Math.max(height, 1),
  };
}

// ============================================================================
// COLOR PALETTES & GROUP COLORS
// ============================================================================

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

// Ordered category list for a categorical column, with the Missing bucket last
// when present.
function getOrderedCategories(colorColumn) {
  const categories = [...colorColumn.values];
  if (colorColumn.has_missing) {
    categories.push(MISSING_VALUE_TOKEN);
  }
  return categories;
}

// Samples whose value in the given column matches a category (or are missing,
// for the Missing bucket).
function filterByCategory(samples, colorColumn, category) {
  return samples.filter((sample) => {
    const value = sample.metadata[colorColumn.name];
    return category === MISSING_VALUE_TOKEN ? value === null : value === category;
  });
}

function getGroupColorMap(groups = groupNames) {
  const orderedGroups = [...new Set(groups)];
  return Object.fromEntries(
    orderedGroups.map((group, index) => [
      group,
      COLOR_PALETTES.Safe.colors[index % COLOR_PALETTES.Safe.colors.length],
    ])
  );
}

// ============================================================================
// SAMPLE-PLOT TRACE BUILDERS
// ============================================================================

function buildTraces(samples) {
  const colorColumn = metadataByName[state.colorBy];
  const featureScaleCircleTraces = buildFeatureScaleCircleTrace();
  const partialOverlayTraces = buildPartialOverlayTraces(samples, colorColumn);
  const featureTraces = buildFeatureTraces();
  const sampleScoreTraces = buildSampleScoreTraces(samples, colorColumn);
  const sizeLegendTraces = buildSizeLegendTraces();
  return appendBarycenterTraces(
    [
      ...featureScaleCircleTraces,
      ...sampleScoreTraces,
      ...sizeLegendTraces,
      ...partialOverlayTraces,
      ...featureTraces,
    ],
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

function buildFeatureScaleCircleTrace() {
  if (!state.showFeatureScaleCircle) {
    return [];
  }

  const radius = state.featureScale;
  const steps = 96;
  const x = [];
  const y = [];
  for (let index = 0; index <= steps; index += 1) {
    const angle = 2 * Math.PI * index / steps;
    x.push(Math.cos(angle) * radius);
    y.push(Math.sin(angle) * radius);
  }

  return [{
    type: 'scatter',
    mode: 'lines',
    name: 'Feature scale circle',
    x,
    y,
    line: {
      color: FEATURE_SCALE_CIRCLE_COLOR,
      width: 1.5,
      dash: 'dot',
    },
    hoverinfo: 'skip',
    showlegend: false,
  }];
}

function buildFeatureTraces() {
  if (!state.showFeatures) {
    return [];
  }

  const themeColors = getThemeColors();
  const rankedFeatures = getRankedFeatures(
    state.topFeatureCount,
    getAllowedGroups('features')
  );
  if (!rankedFeatures.length) {
    return [];
  }

  const groupOrder = isMfa
    ? [...new Set(rankedFeatures.map((feature) => feature.group))].sort()
    : ['Features'];
  const groupColors = getGroupColorMap(groupOrder);
  const labelPlacement = placeFeatureLabels(rankedFeatures, groupColors);

  const traces = [];
  groupOrder.forEach((group) => {
    const groupFeatures = isMfa
      ? rankedFeatures.filter((feature) => feature.group === group)
      : rankedFeatures;
    if (!groupFeatures.length) {
      return;
    }
    const groupLegend = `features:${state.featureSource}:${group}`;
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
      name: `${group} feature endpoints`,
      legendgroup: groupLegend,
      showlegend: false,
      x: groupFeatures.map((feature) => feature.plotX),
      y: groupFeatures.map((feature) => feature.plotY),
      hovertemplate: HOVER_TEMPLATE,
      customdata: groupFeatures.map(buildFeatureHoverText),
      marker: {
        color: groupColors[group],
        size: scalePointSize(9),
        opacity: 0.95,
        symbol: 'triangle-up',
        angle: groupFeatures.map((feature) => featureMarkerAngle(feature)),
        line: {
          color: themeColors.markerLine,
          width: 1,
        },
      },
    });

    pushLabelTraces(
      traces,
      groupLabelPlacement,
      { legendgroup: groupLegend },
      { legendgroup: groupLegend, name: `${group} feature labels` }
    );
  });

  return traces;
}

function featureMarkerAngle(feature) {
  const angleFromXAxis = Math.atan2(feature.plotY, feature.plotX) * 180 / Math.PI;
  return 90 - angleFromXAxis;
}

// Single source of truth for the feature tooltip, used by both the endpoint
// markers and the label placement so the two can never drift apart.
function buildFeatureHoverText(feature) {
  const coordinateMagnitude = Math.hypot(
    componentField(feature, state.xDimension, 'coordinate'),
    componentField(feature, state.yDimension, 'coordinate')
  );
  const correlationMagnitude = Math.hypot(
    componentField(feature, state.xDimension, 'correlation'),
    componentField(feature, state.yDimension, 'correlation')
  );
  const lines = [
    `<b>${feature.variable}</b>`,
    dimLine(state.xDimension, componentField(feature, state.xDimension, 'coordinate'), 'coordinate'),
    dimLine(state.yDimension, componentField(feature, state.yDimension, 'coordinate'), 'coordinate'),
    dimLine(state.xDimension, componentField(feature, state.xDimension, 'correlation'), 'correlation'),
    dimLine(state.yDimension, componentField(feature, state.yDimension, 'correlation'), 'correlation'),
    dimContributionLine(state.xDimension, componentField(feature, state.xDimension, 'contribution')),
    dimContributionLine(state.yDimension, componentField(feature, state.yDimension, 'contribution')),
    dimLine(state.xDimension, componentField(feature, state.xDimension, 'cos2'), 'cos2'),
    dimLine(state.yDimension, componentField(feature, state.yDimension, 'cos2'), 'cos2'),
    `Plane magnitude coordinates: ${formatValue(coordinateMagnitude)}`,
    `Plane magnitude correlation: ${formatValue(correlationMagnitude)}`,
  ];
  if (isMfa) {
    lines.splice(1, 0, `Group: ${feature.group}`);
  }
  return lines.join('<br>');
}

// ============================================================================
// FEATURE RANKING & SELECTION
// ============================================================================

function getSelectedFeatureSource() {
  return featureSources[state.featureSource] ?? featureSources.coordinates;
}

function getFeatureGroups() {
  if (!isMfa) {
    return [];
  }
  return [...new Set(getSelectedFeatureSource().records.map((feature) => feature.group))].sort();
}

function getRankedFeatures(limit = null, allowedFeatureGroups = null) {
  // Rank by source-vector magnitude in the currently displayed 2D plane so the
  // overlay surfaces the variables best represented in the exact view the user
  // is inspecting.
  const selectedSource = getSelectedFeatureSource();
  const selectedFeatures = selectedSource.records;
  const features = allowedFeatureGroups === null
    ? selectedFeatures
    : selectedFeatures.filter((feature) => allowedFeatureGroups.has(feature.group));
  const rankedFeatures = features
    .map((feature) => ({
      ...feature,
      x: featureValue(feature, selectedSource, state.xDimension),
      y: featureValue(feature, selectedSource, state.yDimension),
    }))
    .filter((feature) => Number.isFinite(feature.x) && Number.isFinite(feature.y))
    .map((feature) => ({
      ...feature,
      rankingScore: Math.hypot(feature.x, feature.y),
      display_feature_name: shortenTaxonomyFeatureName(feature.variable),
      plot_feature_name: formatFeaturePlotLabel(feature.variable),
    }))
    .sort((a, b) =>
      b.rankingScore - a.rankingScore ||
      String(a.group ?? '').localeCompare(String(b.group ?? '')) ||
      a.display_feature_name.localeCompare(b.display_feature_name)
    )
    .map((feature, index) => ({
      ...feature,
      rank: index + 1,
      plotX: feature.x * state.featureScale,
      plotY: feature.y * state.featureScale,
    }));

  return limit === null ? rankedFeatures : rankedFeatures.slice(0, limit);
}

function getAllowedGroups(target) {
  if (target === 'features') {
    if (!state.showFeatures) {
      return new Set();
    }
    return isMfa ? state.featureGroups : null;
  }
  if (target === 'partial_samples') {
    return state.showPartialOverlay ? state.partialSampleGroups : new Set();
  }
  return new Set(groupNames);
}

// ============================================================================
// PAYLOAD TABLES (SORT, RENDER, TOOLTIP, EXPORT)
// ============================================================================

function isTableSourceAvailable(source) {
  if (!source || (source.mfaOnly && !isMfa)) {
    return false;
  }
  return getTableSourceRecords(source).length > 0;
}

function getTableSourceRecords(source) {
  return payload[source.recordSet] ?? [];
}

function getDefaultTableSort() {
  const source = TABLE_SOURCES[state.tableSource];
  if (source?.entity === 'dimension') {
    return { column: '_rank', direction: 'asc' };
  }
  return source?.aggregate
    ? { column: 'aggregate', direction: 'desc' }
    : { column: 'x', direction: 'desc' };
}

// Column definitions for the currently selected table. Entity tables show the
// selected X/Y dimensions and, when meaningful, an aggregate metric.
function getTableColumns() {
  const source = TABLE_SOURCES[state.tableSource];
  if (source.entity === 'dimension') {
    return [
      { key: 'label', label: 'Component', defaultDirection: 'asc', type: 'text' },
      { key: 'eigenvalue', label: 'Eigenvalue', defaultDirection: 'desc', type: 'number' },
      { key: 'variance_explained', label: 'Variance explained', defaultDirection: 'desc', type: 'number', format: 'percent' },
      { key: 'cumulative_variance_explained', label: 'Cumulative variance', defaultDirection: 'desc', type: 'number', format: 'percent' },
    ];
  }

  const columns = [
    ...getTableKeyColumns(source),
    { key: 'x', label: `${dimensionLabel(state.xDimension)} ${source.valueLabel}`, defaultDirection: 'desc', type: 'number', format: source.format },
    { key: 'y', label: `${dimensionLabel(state.yDimension)} ${source.valueLabel}`, defaultDirection: 'desc', type: 'number', format: source.format },
  ];
  if (source.aggregate) {
    columns.push({ key: 'aggregate', label: source.aggregateLabel, defaultDirection: 'desc', type: 'number', format: source.format });
  }
  return columns;
}

function getTableKeyColumns(source) {
  if (source.entity === 'sample') {
    return [{ key: 'name', label: 'Sample', defaultDirection: 'asc', type: 'text' }];
  }
  if (source.entity === 'feature') {
    const columns = [
      { key: 'name', label: 'Feature', defaultDirection: 'asc', type: 'text' },
    ];
    if (source.entity === 'feature' && isMfa) {
      columns.push({ key: 'group', label: 'Group', defaultDirection: 'asc', type: 'text' });
    }
    return columns;
  }
  if (source.entity === 'group') {
    return [{ key: 'group', label: 'Group', defaultDirection: 'asc', type: 'text' }];
  }
  if (source.entity === 'partial_sample') {
    return [
      { key: 'sample_id', label: 'Sample', defaultDirection: 'asc', type: 'text' },
      { key: 'group', label: 'Group', defaultDirection: 'asc', type: 'text' },
    ];
  }
  if (source.entity === 'partial_axis') {
    return [
      { key: 'group', label: 'Group', defaultDirection: 'asc', type: 'text' },
      { key: 'partial_component_label', label: 'Partial dim', defaultDirection: 'asc', type: 'text' },
    ];
  }
  return [];
}

// Builds the rows for the selected table: reads the source field for both
// displayed dimensions, computes any aggregate column, and applies the sort.
function getTableRows() {
  const source = TABLE_SOURCES[state.tableSource];
  const columns = getTableColumns();
  const records = getTableSourceRecords(source);
  const rows = source.entity === 'dimension'
    ? records.map((record, index) => ({ ...record, rank: index }))
    : records
        .map((record, index) => {
          const x = componentField(record, state.xDimension, source.field);
          const y = componentField(record, state.yDimension, source.field);
          const row = buildTableRow(source, record);
          row.x = x;
          row.y = y;
          if (source.aggregate) {
            row.aggregate = source.aggregate === 'magnitude' ? Math.hypot(x, y) : x + y;
          }
          row.rank = index;
          return row;
        })
        .filter((row) => Number.isFinite(row.x) && Number.isFinite(row.y));

  const sortableColumns = new Set(columns.map((column) => column.key));
  if (
    state.featureTableSort.column !== '_rank' &&
    !sortableColumns.has(state.featureTableSort.column)
  ) {
    state.featureTableSort = getDefaultTableSort();
  }

  const { column, direction } = state.featureTableSort;
  return rows
    .slice()
    .sort((left, right) => compareTableRows(left, right, column, direction))
    .slice(0, source.entity === 'dimension' ? rows.length : MAX_FEATURE_OVERLAY_COUNT);
}

function buildTableRow(source, record) {
  if (source.entity === 'dimension') {
    return { ...record };
  }

  const row = {};
  if (source.entity === 'sample') {
    row.name = record.sample_id;
    row.fullName = record.sample_id;
  } else if (source.entity === 'feature') {
    row.name = shortenTaxonomyFeatureName(record.variable);
    row.fullName = record.variable;
    row.group = isMfa ? record.group : null;
  } else if (source.entity === 'group') {
    row.group = record.group;
  } else if (source.entity === 'partial_sample') {
    row.sample_id = record.sample_id;
    row.group = record.group;
  } else if (source.entity === 'partial_axis') {
    row.group = record.group;
    row.partial_component = record.partial_component;
    row.partial_component_label = `Partial dim ${record.partial_component + 1}`;
  }

  return row;
}

function compareTableRows(left, right, column, direction) {
  const comparison = column === '_rank'
    ? left.rank - right.rank
    : compareTableCellValues(left[column], right[column]);

  if (comparison !== 0) {
    return direction === 'asc' ? comparison : -comparison;
  }

  return left.rank - right.rank;
}

function compareTableCellValues(left, right) {
  const leftMissing = left === null || left === undefined;
  const rightMissing = right === null || right === undefined;
  if (leftMissing || rightMissing) {
    return Number(leftMissing) - Number(rightMissing);
  }
  if (typeof left === 'number' && typeof right === 'number') {
    return left - right;
  }
  return String(left).localeCompare(String(right));
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

function renderDataTable() {
  const head = document.getElementById('feature-table-head');
  const body = document.getElementById('top-features-table-body');
  const empty = document.getElementById('top-features-empty');
  if (!head || !body || !empty) {
    return;
  }

  const source = TABLE_SOURCES[state.tableSource];
  const columns = getTableColumns();
  renderTableHeader(head, columns);

  const rows = getTableRows();
  updateFeatureTableSortHeaders();
  empty.textContent = rows.length
    ? ''
    : 'No rows for the selected table.';

  const fragment = document.createDocumentFragment();
  rows.forEach((row) => {
    const tr = document.createElement('tr');
    columns.forEach((column) => {
      if (column.key === 'name') {
        tr.appendChild(
          source.entity === 'feature'
            ? buildFeatureNameCell(row)
            : buildSampleNameCell(row)
        );
      } else if (column.type === 'number') {
        tr.appendChild(
          buildFeatureTableCell(formatTableCellValue(row[column.key], column), 'feature-table-number')
        );
      } else {
        tr.appendChild(buildFeatureTableCell(formatTableCellValue(row[column.key], column)));
      }
    });
    fragment.appendChild(tr);
  });
  body.replaceChildren(fragment);
}

function formatTableCellValue(value, column) {
  if (value === null || value === undefined) {
    return '';
  }
  if (column.format === 'fractionPercent') {
    return formatPercent(value);
  }
  if (column.format === 'percent') {
    return `${formatValue(value)}%`;
  }
  return formatValue(value);
}

function renderTableHeader(head, columns) {
  const row = document.createElement('tr');
  columns.forEach((column) => {
    const th = document.createElement('th');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'feature-table-sort';
    button.dataset.featureSort = column.key;
    button.dataset.defaultDirection = column.defaultDirection;

    const label = document.createElement('span');
    label.textContent = column.label;
    const indicator = document.createElement('span');
    indicator.className = 'feature-table-sort-indicator';
    indicator.setAttribute('aria-hidden', 'true');

    button.appendChild(label);
    button.appendChild(indicator);
    th.appendChild(button);
    row.appendChild(th);
  });
  head.replaceChildren(row);
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

function buildFeatureNameCell(row) {
  const tooltipText = row.fullName;
  const cell = buildFeatureTableCell(row.name, 'feature-name-cell');
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

function buildSampleNameCell(row) {
  const cell = document.createElement('td');
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'sample-name-button';
  button.textContent = row.name;
  button.addEventListener('click', () => {
    toggleSelectedSample(row.fullName, { scrollToPlot: true });
  });
  cell.appendChild(button);
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

// ============================================================================
// SAMPLE DETAILS PANEL
// ============================================================================

// Fixed panel that shows the selected sample's selected-axis metrics first,
// followed by metadata in table form.
function renderSampleDetailsPanel() {
  const panel = document.getElementById('sample-details');
  if (!panel) {
    return;
  }

  const sample = state.selectedSampleId ? samplesById[state.selectedSampleId] : null;
  if (!sample) {
    panel.replaceChildren(buildSampleDetailsEmptyState());
    return;
  }

  const title = document.createElement('div');
  title.className = 'sample-details-title';
  title.textContent = sample.sample_id;

  panel.replaceChildren(
    title,
    buildSampleMetricsTable(sample),
    buildSampleMetadataTable(sample)
  );
}

function buildSampleDetailsEmptyState() {
  const empty = document.createElement('div');
  empty.className = 'sample-details-empty';
  empty.textContent = 'Click a sample to view details.';
  return empty;
}

function buildSampleMetricsTable(sample) {
  const table = buildSampleDetailsTable('sample-details-metrics');
  const head = document.createElement('thead');
  const headerRow = document.createElement('tr');
  ['', dimensionLabel(state.xDimension), dimensionLabel(state.yDimension)].forEach(
    (label, index) => {
      const className = index === 0 ? 'sample-details-name' : '';
      headerRow.appendChild(buildSampleDetailsCell('th', label, className));
    }
  );
  head.appendChild(headerRow);

  const body = document.createElement('tbody');
  body.appendChild(
    buildSampleMetricRow('coordinate', [
      formatValue(componentField(sample, state.xDimension, 'coordinate')),
      formatValue(componentField(sample, state.yDimension, 'coordinate')),
    ])
  );
  body.appendChild(
    buildSampleMetricRow('contribution', [
      formatPercent(componentField(sample, state.xDimension, 'contribution')),
      formatPercent(componentField(sample, state.yDimension, 'contribution')),
    ])
  );
  body.appendChild(
    buildSampleMetricRow('cos2', [
      formatValue(componentField(sample, state.xDimension, 'cos2')),
      formatValue(componentField(sample, state.yDimension, 'cos2')),
    ])
  );

  table.appendChild(head);
  table.appendChild(body);
  return table;
}

function buildSampleMetadataTable(sample) {
  const table = buildSampleDetailsTable('sample-details-metadata');
  const body = document.createElement('tbody');
  metadataColumns.forEach((column) => {
    const row = document.createElement('tr');
    row.appendChild(buildSampleDetailsCell('th', column.name, 'sample-details-name'));
    row.appendChild(
      buildSampleDetailsCell(
        'td',
        formatMetadataValue(sample.metadata[column.name]),
        'sample-details-value'
      )
    );
    body.appendChild(row);
  });
  table.appendChild(body);
  return table;
}

function buildSampleMetricRow(label, values) {
  const row = document.createElement('tr');
  row.appendChild(buildSampleDetailsCell('th', label, 'sample-details-name'));
  values.forEach((value) => {
    row.appendChild(buildSampleDetailsCell('td', value, 'sample-details-value'));
  });
  return row;
}

function buildSampleDetailsTable(className) {
  const table = document.createElement('table');
  table.className = `sample-details-table ${className}`;
  return table;
}

function buildSampleDetailsCell(tagName, value, className = '') {
  const cell = document.createElement(tagName);
  if (className) {
    cell.className = className;
  }
  cell.textContent = value;
  return cell;
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
  const columns = getTableColumns();
  const rows = getTableRows();
  const header = columns.map((column) => column.label);
  const lines = [
    header.map(escapeTsvValue).join('\t'),
    // Export the full (unshortened) name for the entity column, and the payload
    // values otherwise (i.e. more precision than the rounded on-screen table,
    // though still trimmed once at the Python export step).
    ...rows.map((row) =>
      columns
        .map((column) => rawTableCellValue(row, column))
        .map(escapeTsvValue)
        .join('\t')
    ),
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

function rawTableCellValue(row, column) {
  if (column.key === 'name') {
    return row.fullName ?? row.name;
  }
  return row[column.key] ?? '';
}

function escapeTsvValue(value) {
  return String(value).replace(/\t/g, ' ').replace(/\r?\n/g, ' ');
}

function buildFeatureTableDownloadFilename() {
  const source = TABLE_SOURCES[state.tableSource];
  if (source?.entity === 'dimension') {
    return `${analysisType}-${state.tableSource}.tsv`;
  }
  const xLabel = dimensionFileLabel(state.xDimension);
  const yLabel = dimensionFileLabel(state.yDimension);
  return `${analysisType}-${state.tableSource}-${xLabel}-vs-${yLabel}.tsv`;
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

// ============================================================================
// TRACE BUILDERS: PARTIAL OVERLAY, MARKERS, SIZE LEGEND, BARYCENTER
// ============================================================================

function buildPartialOverlayTraces(samples, colorColumn) {
  if (
    !state.showPartialOverlay ||
    !partialSamples.length
  ) {
    return [];
  }

  const visibleSampleIds = new Set(samples.map((sample) => sample.sample_id));
  const allowedPartialGroups = getAllowedGroups('partial_samples');
  const visibleSamplesById = Object.fromEntries(
    samples.map((sample) => [sample.sample_id, sample])
  );
  const visiblePartialSamples = partialSamples.filter(
    (entry) =>
      allowedPartialGroups.has(entry.group) &&
      visibleSampleIds.has(entry.sample_id) &&
      partialSampleValue(entry, state.xDimension) !== undefined &&
      partialSampleValue(entry, state.yDimension) !== undefined
  );

  if (!visiblePartialSamples.length) {
    return [];
  }

  const groupColors = getGroupColorMap();
  const traces = [];

  if (colorColumn?.type === 'categorical') {
    const partialLegendGroupsShown = new Set();

    getOrderedCategories(colorColumn).forEach((category) => {
      const categorySamples = filterByCategory(samples, colorColumn, category);
      if (!categorySamples.length) {
        return;
      }

      const categorySampleIds = new Set(categorySamples.map((sample) => sample.sample_id));
      groupNames.forEach((group) => {
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

  groupNames.forEach((group) => {
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
    x.push(
      sampleValue(sample, state.xDimension),
      partialSampleValue(entry, state.xDimension),
      null
    );
    y.push(
      sampleValue(sample, state.yDimension),
      partialSampleValue(entry, state.yDimension),
      null
    );
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
    x: groupEntries.map((entry) => partialSampleValue(entry, state.xDimension)),
    y: groupEntries.map((entry) => partialSampleValue(entry, state.yDimension)),
    customdata: groupEntries.map(buildPartialHoverText),
    hovertemplate: HOVER_TEMPLATE,
    marker: {
      color,
      size: getPointSizes(groupEntries, 6, (entry) => samplesById[entry.sample_id]),
      opacity: state.pointOpacity,
      symbol: 'diamond-open',
      line: { color, width: 2 },
    },
  };
}

// Shared sample-marker scatter used by the single, categorical, and numeric
// sample traces. Callers supply marker overrides (color, symbol, colorbar, ...)
// on top of the common size/opacity/border.
function buildSampleScatterTrace(samples, name, { showlegend = true, legendgroup, marker = {} } = {}) {
  return {
    type: 'scatter',
    mode: 'markers',
    name: formatSampleLegendName(name, samples),
    legendgroup,
    showlegend,
    x: samples.map((sample) => sampleValue(sample, state.xDimension)),
    y: samples.map((sample) => sampleValue(sample, state.yDimension)),
    // Sample points suppress the native Plotly label and carry only their id,
    // so click handling can toggle the fixed sample details panel.
    customdata: samples.map((sample) => sample.sample_id),
    text: samples.map(buildSampleHoverText),
    hovertemplate: '%{text}<extra></extra>',
    marker: {
      size: getPointSizes(samples, 8),
      opacity: state.pointOpacity,
      line: buildSamplePointMarkerLine(samples, getThemeColors().markerLine, 1),
      ...marker,
    },
  };
}

function buildSampleHoverText(sample) {
  return [
    `<b>${sample.sample_id}</b>`,
    dimLine(state.xDimension, componentField(sample, state.xDimension, 'coordinate'), 'coordinate'),
    dimLine(state.yDimension, componentField(sample, state.yDimension, 'coordinate'), 'coordinate'),
    dimContributionLine(
      state.xDimension,
      componentField(sample, state.xDimension, 'contribution')
    ),
    dimContributionLine(
      state.yDimension,
      componentField(sample, state.yDimension, 'contribution')
    ),
    `${dimensionLabel(state.xDimension)} cos2: ${formatValue(
      componentField(sample, state.xDimension, 'cos2')
    )}`,
    `${dimensionLabel(state.yDimension)} cos2: ${formatValue(
      componentField(sample, state.yDimension, 'cos2')
    )}`,
  ].join('<br>');
}

function buildSingleTrace(samples, color, name, options = {}) {
  return buildSampleScatterTrace(samples, name, {
    showlegend: options.showlegend,
    legendgroup: options.legendgroup,
    marker: {
      color,
      symbol: options.symbol ?? 'circle',
    },
  });
}

function formatSampleLegendName(name, samples) {
  return `${name} (n=${samples.length})`;
}

function scalePointSize(baseSize) {
  return baseSize * state.pointSizeScale;
}

// Works for both plain samples and partial-sample entries: pass a resolver that
// maps each item to the sample carrying the size metadata.
function getPointSizes(items, baseSize, resolveSample = (item) => item) {
  const sizeColumn = metadataByName[state.sizeBy];
  if (!sizeColumn || sizeColumn.type !== 'numeric') {
    return scalePointSize(baseSize);
  }

  return items.map((item) =>
    scaleMetadataPointSize(resolveSample(item), sizeColumn, baseSize)
  );
}

function scaleMetadataPointSize(sample, sizeColumn, baseSize) {
  const value = sample?.metadata[sizeColumn.name];
  if (value === null || !Number.isFinite(value) || sizeColumn.max <= sizeColumn.min) {
    return scalePointSize(baseSize);
  }

  const fraction = (value - sizeColumn.min) / (sizeColumn.max - sizeColumn.min);
  const boundedFraction = Math.max(0, Math.min(1, fraction));
  return scaleMetadataFractionPointSize(boundedFraction, baseSize);
}

function scaleMetadataFractionPointSize(fraction, baseSize) {
  return scalePointSize(baseSize * (0.75 + 1.5 * fraction));
}

function buildSizeLegendTraces() {
  const sizeColumn = metadataByName[state.sizeBy];
  if (!sizeColumn || sizeColumn.type !== 'numeric' || sizeColumn.max <= sizeColumn.min) {
    return [];
  }

  const markerLine = buildStaticSamplePointMarkerLine(getThemeColors().markerLine, 1);
  const sizeMarker = (size) => ({
    color: DEFAULT_MARKER_COLOR,
    size,
    opacity: state.pointOpacity,
    symbol: 'circle',
    line: markerLine,
  });
  return [
    buildSizeLegendEntryTrace(`Size by: ${sizeColumn.name}`),
    buildSizeLegendEntryTrace(
      `min: ${formatValue(sizeColumn.min)}`,
      sizeMarker(scaleMetadataFractionPointSize(0, 8))
    ),
    buildSizeLegendEntryTrace(
      `max: ${formatValue(sizeColumn.max)}`,
      sizeMarker(scaleMetadataFractionPointSize(1, 8))
    ),
  ];
}

// A legend-only (off-canvas) trace. With a marker it shows a sized dot; without
// one it renders an invisible line, used as the size-legend header row.
function buildSizeLegendEntryTrace(name, marker = null) {
  const trace = {
    type: 'scatter',
    mode: marker ? 'markers' : 'lines',
    name,
    legendgroup: 'size-legend',
    showlegend: true,
    x: [null],
    y: [null],
    hoverinfo: 'skip',
  };
  if (marker) {
    trace.marker = marker;
  } else {
    trace.line = { color: 'rgba(0, 0, 0, 0)', width: 0 };
  }
  return trace;
}

function buildStaticSamplePointMarkerLine(color, width) {
  return state.showPointBorder ? { color, width } : { color, width: 0 };
}

function buildSamplePointMarkerLine(samples, color, width) {
  return {
    color: samples.map((sample) =>
      sample.sample_id === state.selectedSampleId ? '#000000' : color
    ),
    width: samples.map((sample) => {
      if (sample.sample_id === state.selectedSampleId) {
        return 3;
      }
      return state.showPointBorder ? width : 0;
    }),
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
    traces.push(buildSampleScatterTrace(numericSamples, colorColumn.name, {
      showlegend: false,
      marker: {
        color: numericSamples.map((sample) => sample.metadata[colorColumn.name]),
        colorscale: getNumericColorscale(state.colorPalette),
        colorbar: {
          title: {
            text: formatSampleLegendName(colorColumn.name, numericSamples),
            font: buildPlotFont(themeColors),
          },
          x: 1.02,
          xanchor: 'left',
          y: SAMPLE_NUMERIC_COLORBAR_Y,
          yanchor: 'top',
          len: SAMPLE_NUMERIC_COLORBAR_LENGTH,
          thickness: 18,
          tickfont: buildPlotFont(themeColors),
        },
        cmin: colorColumn.min,
        cmax: colorColumn.max,
      },
    }));
  }

  if (missingSamples.length) {
    traces.push(buildSingleTrace(missingSamples, '#94A3B8', 'Missing'));
  }

  return traces;
}

function buildCategoricalTraces(samples, colorColumn) {
  const palette = getCategoricalColors(getCategoricalLevelCount(colorColumn));
  const symbols = getCategoricalSymbols(getCategoricalLevelCount(colorColumn));

  return getOrderedCategories(colorColumn)
    .map((category, index) => {
      const subset = filterByCategory(samples, colorColumn, category);

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
    const orderedCategories = getOrderedCategories(colorColumn);
    const palette = getCategoricalColors(orderedCategories.length);
    orderedCategories.forEach((category, index) => {
      const subset = filterByCategory(samples, colorColumn, category);
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
    sampleValue(sample, state.xDimension),
    sampleValue(sample, state.yDimension),
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

// Cycle `count` entries out of the active palette's `key` array (colors or
// symbols), wrapping around and falling back when the palette lacks that key.
function cyclePalette(count, key, fallback) {
  const palette = COLOR_PALETTES[state.colorPalette] ?? COLOR_PALETTES.Plotly;
  const values = palette[key] ?? fallback;
  return Array.from({ length: count }, (_, index) => values[index % values.length]);
}

function getCategoricalColors(count) {
  return cyclePalette(count, 'colors', COLOR_PALETTES.Plotly.colors);
}

function getCategoricalSymbols(count) {
  return cyclePalette(count, 'symbols', ['circle']);
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

// ============================================================================
// SHARED PLOT CONFIG, LAYOUT HELPERS & MAIN LAYOUT
// ============================================================================

// Mode-bar buttons removed from every secondary (non-interactive) plot.
const SECONDARY_PLOT_MODEBAR_REMOVE = [
  'lasso2d',
  'select2d',
  'zoom2d',
  'pan2d',
  'zoomIn2d',
  'zoomOut2d',
  'autoScale2d',
  'resetScale2d',
];

// A mode-bar button that exports a plot in the given raster/vector format.
// `filename` includes the extension; downloadPlotImage strips it back off.
function buildImageDownloadButton(label, plotId, filename, format) {
  return {
    name: label,
    icon: Plotly.Icons.camera,
    click: () => {
      downloadPlotImage(plotId, filename, format);
    },
  };
}

// Shared Plotly config for the four secondary plots: PNG via the built-in
// camera, an added SVG export, and a trimmed mode bar.
function buildSecondaryPlotConfig(plotId, baseFilename, { width = 1200, height = 700 } = {}) {
  return {
    responsive: true,
    displaylogo: false,
    toImageButtonOptions: {
      format: 'png',
      filename: baseFilename,
      width,
      height,
      scale: 2,
    },
    modeBarButtonsToAdd: [
      buildImageDownloadButton('Download SVG', plotId, `${baseFilename}.svg`, 'svg'),
    ],
    modeBarButtonsToRemove: SECONDARY_PLOT_MODEBAR_REMOVE,
  };
}

// Common layout scaffolding (transparent background + themed base font).
function buildBaseLayout(themeColors, overrides = {}) {
  return {
    paper_bgcolor: 'rgba(0, 0, 0, 0)',
    plot_bgcolor: 'rgba(255, 255, 255, 0)',
    font: {
      color: themeColors.font,
      family: themeColors.fontFamily,
      size: themeColors.fontSize,
    },
    ...overrides,
  };
}

// Axis with the themed grid + tick font pre-filled; overrides win.
function buildThemedAxis(themeColors, overrides = {}) {
  return {
    gridcolor: themeColors.grid,
    gridwidth: 1,
    tickfont: buildPlotFont(themeColors),
    ...overrides,
  };
}

// The zero-line styling shared by the scatter-style plots.
function themedZeroline(themeColors) {
  return {
    zeroline: true,
    zerolinecolor: themeColors.zeroline,
    zerolinewidth: 1,
  };
}

function buildLayout(traces) {
  const themeColors = getThemeColors();
  const legendRightMargin = computeSampleLegendRightMargin(traces);
  const legendY = hasSampleNumericColorbar(traces) ? SAMPLE_LEGEND_BELOW_COLORBAR_Y : 1;
  const sharedGridStep = computeSharedSampleGridStep(traces);

  return buildBaseLayout(themeColors, {
    dragmode: 'pan',
    hovermode: 'closest',
    margin: { t: 32, r: legendRightMargin, b: 78, l: 80 },
    legend: {
      orientation: 'v',
      groupclick: 'togglegroup',
      yanchor: 'top',
      y: legendY,
      xanchor: 'left',
      x: 1.02,
      font: buildPlotFont(themeColors),
    },
    xaxis: buildThemedAxis(themeColors, {
      title: {
        text: dimensionAxisTitle(state.xDimension),
        font: buildPlotFont(themeColors),
      },
      scaleanchor: 'y',
      scaleratio: 1,
      tickmode: 'linear',
      tick0: 0,
      dtick: sharedGridStep,
      ...themedZeroline(themeColors),
    }),
    yaxis: buildThemedAxis(themeColors, {
      title: {
        text: dimensionAxisTitle(state.yDimension),
        font: buildPlotFont(themeColors),
      },
      tickmode: 'linear',
      tick0: 0,
      dtick: sharedGridStep,
      ...themedZeroline(themeColors),
    }),
  });
}

function applySamplePlotSquareDataArea(layout) {
  const samplePlotShell = document.querySelector('.plot-shell-main');
  const samplePlot = document.getElementById('sample-plot');
  const samplePlotLayout = document.querySelector('.sample-plot-layout');
  const sampleDetailsPanel = hasMetadata
    ? document.querySelector('.sample-details-panel')
    : null;
  if (!samplePlotShell || !samplePlot || !samplePlotLayout) {
    return;
  }

  const margin = layout.margin;
  const layoutRect = samplePlotLayout.getBoundingClientRect();
  const shellStyle = window.getComputedStyle(samplePlotShell);
  const layoutStyle = window.getComputedStyle(samplePlotLayout);
  const shellHorizontalBorder =
    parseFloat(shellStyle.borderLeftWidth) + parseFloat(shellStyle.borderRightWidth);
  const shellVerticalBorder =
    parseFloat(shellStyle.borderTopWidth) + parseFloat(shellStyle.borderBottomWidth);
  const columnGap = parseFloat(layoutStyle.columnGap) || 0;
  const panelWidth = sampleDetailsPanel?.getBoundingClientRect().width ?? 0;
  const isSideBySide =
    sampleDetailsPanel &&
    Math.abs(sampleDetailsPanel.offsetTop - samplePlotShell.offsetTop) < 2;
  const availableShellWidth = isSideBySide
    ? layoutRect.width - panelWidth - columnGap
    : layoutRect.width;
  const availablePlotWidth = Math.max(1, availableShellWidth - shellHorizontalBorder);
  const dataAreaSize = Math.max(
    1,
    Math.floor(availablePlotWidth - margin.l - margin.r)
  );
  const width = dataAreaSize + margin.l + margin.r;
  const height = dataAreaSize + margin.t + margin.b;
  const shellWidth = width + shellHorizontalBorder;
  const shellHeight = height + shellVerticalBorder;

  samplePlotShell.style.width = `${shellWidth}px`;
  samplePlotShell.style.height = `${shellHeight}px`;
  samplePlot.style.width = `${width}px`;
  samplePlot.style.height = `${height}px`;
  samplePlotLayout.style.setProperty('--sample-plot-height', `${shellHeight}px`);
  layout.width = width;
  layout.height = height;
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

// ============================================================================
// SECONDARY PLOTS (GROUP, PARTIAL AXES, VARIANCE) & LABEL PLACEMENT
// ============================================================================

function renderGroupPlot() {
  const themeColors = getThemeColors();
  const groups = groupSummary.filter(
    (entry) =>
      groupCoordinateValue(entry, state.xDimension) !== undefined &&
      groupCoordinateValue(entry, state.yDimension) !== undefined
  );
  const groupColors = getGroupColorMap(groups.map((entry) => entry.group));
  const labelPlacement = placeGroupInertiaLabels(groups, groupColors);

  const trace = {
    type: 'scatter',
    mode: 'markers',
    name: 'Groups',
    x: groups.map((entry) => groupCoordinateValue(entry, state.xDimension)),
    y: groups.map((entry) => groupCoordinateValue(entry, state.yDimension)),
    hovertemplate: HOVER_TEMPLATE,
    customdata: groups.map(
      (entry) => `<b>${entry.group}</b><br>${buildGroupHoverText(entry)}`
    ),
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
  const traces = [trace];
  pushLabelTraces(traces, labelPlacement);

  Plotly.react(
    'group-plot',
    traces,
    buildGroupLayout(),
    buildSecondaryPlotConfig('group-plot', `${analysisType}-group-partial-inertia`, {
      width: 1200,
      height: 1200,
    })
  );

  updateGroupSummary(groups);
}

function buildGroupHoverText(entry) {
  return [
    dimLine(state.xDimension, groupCoordinateValue(entry, state.xDimension), 'partial inertia'),
    dimLine(state.yDimension, groupCoordinateValue(entry, state.yDimension), 'partial inertia'),
    dimContributionLine(state.xDimension, groupContributionValue(entry, state.xDimension)),
    dimContributionLine(state.yDimension, groupContributionValue(entry, state.yDimension)),
    dimLine(state.xDimension, groupCos2Value(entry, state.xDimension), 'cos2'),
    dimLine(state.yDimension, groupCos2Value(entry, state.yDimension), 'cos2'),
  ].join('<br>');
}

function placeGroupInertiaLabels(groups, groupColors) {
  const items = groups.map((entry) => ({
    anchorX: groupCoordinateValue(entry, state.xDimension),
    anchorY: groupCoordinateValue(entry, state.yDimension),
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

function placeFeatureLabels(features, groupColors) {
  const items = features.map((feature) => ({
    anchorX: feature.plotX,
    anchorY: feature.plotY,
    color: groupColors[isMfa ? feature.group : 'Features'],
    group: isMfa ? feature.group : 'Features',
    hoverText: buildFeatureHoverText(feature),
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
      family: state.fontFamily,
    },
    hoverinfo: 'skip',
    cliponaxis: false,
    showlegend: false,
    ...traceOptions,
  };
}

// Push the connector traces + (if any) the label trace for a placement onto an
// existing trace array. Shared by the feature, group, and partial-axes plots.
function pushLabelTraces(traces, labelPlacement, connectorOptions = {}, labelOptions = {}) {
  traces.push(...buildPlotLabelConnectorTraces(labelPlacement, connectorOptions));
  const labelTrace = buildPlotLabelTrace(labelPlacement, state.fontSize, labelOptions);
  if (labelTrace) {
    traces.push(labelTrace);
  }
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
  return buildBaseLayout(themeColors, {
    margin: SECONDARY_SQUARE_PLOT_MARGIN,
    showlegend: false,
    xaxis: buildThemedAxis(themeColors, {
      title: {
        text: dimensionLabel(state.xDimension),
        font: buildPlotFont(themeColors),
      },
      range: [0, 1],
      fixedrange: true,
      constrain: 'domain',
      scaleanchor: 'y',
      scaleratio: 1,
      automargin: true,
      ...themedZeroline(themeColors),
    }),
    yaxis: buildThemedAxis(themeColors, {
      title: {
        text: dimensionLabel(state.yDimension),
        font: buildPlotFont(themeColors),
      },
      range: [0, 1],
      fixedrange: true,
      constrain: 'domain',
      automargin: true,
      ...themedZeroline(themeColors),
    }),
    annotations: [],
  });
}

// Sets the text of a summary element, tolerating a missing element.
function setSummary(id, text) {
  const target = document.getElementById(id);
  if (target) {
    target.textContent = text;
  }
}

function updateGroupSummary(groups) {
  setSummary('group-summary-text', groups.length ? `${groups.length} groups shown` : '');
}

function renderPartialAxesPlot() {
  const themeColors = getThemeColors();
  const partialAxes = (payload.partial_axes ?? []).filter(
    (entry) => entry.partial_component < state.partialAxisCount
  );
  const groupColors = getGroupColorMap();

  const vectorSeries = partialAxes.map((entry) => {
    const partialAxis = entry.partial_component + 1;
    const vector = buildPartialAxesVector(entry);
    if (!vector) {
      return null;
    }

    const label = `${entry.group} partial dim ${partialAxis}`;
    const color = groupColors[entry.group];

    return {
      color,
      hoverText: [
        `<b>${entry.group}</b>`,
        `Partial dim ${partialAxis}`,
        dimLine(state.xDimension, componentField(entry, state.xDimension, 'correlation'), 'correlation'),
        dimLine(state.yDimension, componentField(entry, state.yDimension, 'correlation'), 'correlation'),
        dimContributionLine(state.xDimension, componentField(entry, state.xDimension, 'contribution')),
        dimContributionLine(state.yDimension, componentField(entry, state.yDimension, 'contribution')),
      ].join('<br>'),
      label,
      seriesKey: `${entry.group}::${entry.partial_component}`,
      vector,
    };
  }).filter(Boolean);
  const labelPlacement = placePartialAxesLabels(vectorSeries);
  const traces = vectorSeries.flatMap((series) =>
    buildPartialAxesVectorTrace(series, themeColors)
  );
  pushLabelTraces(traces, labelPlacement);

  traces.unshift(buildPartialAxesCircleBoundary());

  Plotly.react(
    'partial-axes-plot',
    traces,
    buildPartialAxesLayout(),
    buildSecondaryPlotConfig('partial-axes-plot', `${analysisType}-partial-axes`)
  );

  updatePartialAxesSummary(partialAxes);
}

// A partial-axis vector is drawn as a non-hoverable line from the origin plus a
// single hoverable endpoint marker, so the shared (0, 0) origin never triggers
// an (empty) hover label.
function buildPartialAxesVectorTrace(series, themeColors) {
  const legendgroup = `axes:${series.seriesKey}`;
  return [
    {
      type: 'scatter',
      mode: 'lines',
      name: series.label,
      legendgroup,
      x: [0, series.vector.x],
      y: [0, series.vector.y],
      line: {
        color: withAlpha(series.color, 0.7),
        width: 2,
      },
      hoverinfo: 'skip',
      showlegend: false,
    },
    {
      type: 'scatter',
      mode: 'markers',
      name: series.label,
      legendgroup,
      x: [series.vector.x],
      y: [series.vector.y],
      customdata: [series.hoverText],
      hovertemplate: HOVER_TEMPLATE,
      marker: {
        color: series.color,
        size: 9,
        symbol: 'circle',
        line: {
          color: themeColors.markerLine,
          width: 1,
        },
      },
      showlegend: false,
    },
  ];
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

function buildPartialAxesVector(entry) {
  const x = componentField(entry, state.xDimension, 'correlation');
  const y = componentField(entry, state.yDimension, 'correlation');
  if (!Number.isFinite(x) || !Number.isFinite(y)) {
    return null;
  }

  return { x, y };
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
  return buildBaseLayout(themeColors, {
    margin: SECONDARY_SQUARE_PLOT_MARGIN,
    showlegend: false,
    xaxis: buildThemedAxis(themeColors, {
      title: {
        text: dimensionLabel(state.xDimension),
        font: buildPlotFont(themeColors),
      },
      range: PARTIAL_AXES_X_RANGE,
      constrain: 'domain',
      scaleanchor: 'y',
      scaleratio: 1,
      automargin: true,
      ...themedZeroline(themeColors),
    }),
    yaxis: buildThemedAxis(themeColors, {
      title: {
        text: dimensionLabel(state.yDimension),
        font: buildPlotFont(themeColors),
      },
      range: PARTIAL_AXES_Y_RANGE,
      constrain: 'domain',
      automargin: true,
      ...themedZeroline(themeColors),
    }),
    annotations: [],
  });
}

function updatePartialAxesSummary(partialAxes) {
  if (!partialAxes.length) {
    setSummary('partial-axes-summary', '');
    return;
  }

  const groups = new Set(partialAxes.map((entry) => entry.group));
  const axes = new Set(partialAxes.map((entry) => `${entry.group}::${entry.partial_component}`));
  setSummary('partial-axes-summary', `${axes.size} partial axes across ${groups.size} groups`);
}

function renderVariancePlot() {
  const components = payload.dimensions.filter(
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
        selectedDimensions.has(component.component)
          ? SELECTED_DIMENSION_COLOR
          : VARIANCE_MARKER_COLOR
      ),
      line: {
        color: themeColors.markerLine,
        width: 1,
      },
    },
    customdata: components.map(buildVarianceHoverText),
    hovertemplate: HOVER_TEMPLATE,
  };

  Plotly.react(
    'variance-plot',
    [barTrace],
    buildVarianceLayout(),
    buildSecondaryPlotConfig(
      'variance-plot',
      `${analysisType}-explained-variance-by-component`
    )
  );

  renderCumulativeVariancePlot(components, themeColors);
  updateVarianceSummary(components);
}

function renderCumulativeVariancePlot(components, themeColors) {
  const selectedDimensions = new Set([state.xDimension, state.yDimension]);
  const cumulativeTrace = {
    type: 'scatter',
    mode: 'lines+markers',
    name: 'Cumulative explained variance',
    x: components.map((component) => component.label),
    y: components.map((component) => component.cumulative_variance_explained),
    line: {
      color: VARIANCE_MARKER_COLOR,
      width: 3,
    },
    marker: {
      color: components.map((component) =>
        selectedDimensions.has(component.component)
          ? SELECTED_DIMENSION_COLOR
          : VARIANCE_MARKER_COLOR
      ),
      size: 8,
      line: {
        color: themeColors.markerLine,
        width: 1,
      },
    },
    customdata: components.map(buildVarianceHoverText),
    hovertemplate: HOVER_TEMPLATE,
  };

  Plotly.react(
    'cumulative-variance-plot',
    [cumulativeTrace],
    buildCumulativeVarianceLayout(),
    buildSecondaryPlotConfig(
      'cumulative-variance-plot',
      `${analysisType}-cumulative-explained-variance`
    )
  );
  updateCumulativeSummary(components);
}

function buildVarianceLayout() {
  const themeColors = getThemeColors();
  return buildBaseLayout(themeColors, {
    margin: VARIANCE_PLOT_MARGIN,
    bargap: 0.24,
    xaxis: {
      tickfont: buildPlotFont(themeColors),
    },
    yaxis: buildThemedAxis(themeColors, {
      title: {
        text: 'Explained variance (%)',
        font: buildPlotFont(themeColors),
      },
      rangemode: 'tozero',
    }),
    annotations: [],
  });
}

function buildCumulativeVarianceLayout() {
  const themeColors = getThemeColors();
  return buildBaseLayout(themeColors, {
    margin: CUMULATIVE_VARIANCE_PLOT_MARGIN,
    xaxis: buildThemedAxis(themeColors, {
      showgrid: true,
      gridcolor: themeColors.gridSoft,
    }),
    yaxis: buildThemedAxis(themeColors, {
      title: {
        text: 'Cumulative explained variance (%)',
        font: buildPlotFont(themeColors),
      },
      range: [0, 104],
      zeroline: true,
    }),
    annotations: [],
  });
}

// ============================================================================
// THEME, FONTS & FORMATTING UTILITIES
// ============================================================================

function getThemeColors() {
  const styles = getComputedStyle(document.body);
  return {
    font: styles.getPropertyValue('--plot-font').trim(),
    fontFamily: state.fontFamily,
    grid: styles.getPropertyValue('--plot-grid').trim(),
    gridSoft: styles.getPropertyValue('--plot-grid-soft').trim(),
    zeroline: styles.getPropertyValue('--plot-zero').trim(),
    annotation: styles.getPropertyValue('--plot-annotation').trim(),
    markerLine: styles.getPropertyValue('--plot-marker-line').trim(),
    fontSize: state.fontSize,
  };
}

function buildPlotFont(themeColors, size = themeColors.fontSize) {
  return {
    color: themeColors.font,
    family: themeColors.fontFamily,
    size,
  };
}

// One "<dim label>[ <suffix>]: <value>" hover line. Shared by every hover
// builder so the coordinate/contribution/cos2/correlation lines all match.
function dimLine(component, value, suffix = '') {
  const label = suffix
    ? `${dimensionLabel(component)} ${suffix}`
    : dimensionLabel(component);
  return `${label}: ${formatValue(value)}`;
}

// Contributions are stored as fractions (0-1); everywhere they are shown they
// are rendered as percentages.
function formatPercent(value) {
  return typeof value === 'number' ? `${formatValue(value * 100)}%` : formatValue(value);
}

// Contribution hover line, using the same layout as dimLine but as a percentage.
function dimContributionLine(component, value) {
  return `${dimensionLabel(component)} contribution: ${formatPercent(value)}`;
}

function buildPartialHoverText(entry) {
  return [
    `<b>${entry.sample_id}</b>`,
    `Group: ${entry.group}`,
    dimLine(state.xDimension, partialSampleValue(entry, state.xDimension), 'coordinate'),
    dimLine(state.yDimension, partialSampleValue(entry, state.yDimension), 'coordinate'),
  ].join('<br>');
}

function buildVarianceHoverText(component) {
  return [
    `<b>${component.label}</b>`,
    `Explained variance: ${formatValue(component.variance_explained)}%`,
    `Cumulative explained variance: ${formatValue(component.cumulative_variance_explained)}%`,
    `Eigenvalue: ${formatValue(component.eigenvalue)}`,
  ].join('<br>');
}

function updateVarianceSummary(components) {
  const totalExplained = components.reduce(
    (sum, component) => sum + component.variance_explained,
    0
  );
  setSummary(
    'variance-summary',
    `${formatValue(totalExplained)}% across ${components.length} components`
  );
}

function updateCumulativeSummary(components) {
  const finalComponent = components.length ? components[components.length - 1] : null;
  const finalValue = finalComponent?.cumulative_variance_explained ?? 0;
  setSummary(
    'cumulative-summary',
    `${formatValue(finalValue)}% at component ${components.length}`
  );
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
