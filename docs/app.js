const BASE_URL = 'https://raw.githubusercontent.com/treehub/indices/main';

document.addEventListener('DOMContentLoaded', () => {
    loadPlatforms();

    document.getElementById('platform-search').addEventListener('input', (e) => {
        filterPlatforms(e.target.value);
    });
});

let platformsData = {};

async function loadPlatforms() {
    const platformListEle = document.getElementById('platform-list');
    try {
        let res = await fetch(`${BASE_URL}/registry.json`);
        if (!res.ok) {
            res = await fetch('../registry.json');
        }

        if (!res.ok) {
            throw new Error(`Failed to fetch registry (Status: ${res.status})`);
        }

        const text = await res.text();
        try {
            platformsData = JSON.parse(text);
        } catch (parseError) {
            throw new Error(`Invalid JSON in registry`);
        }

        renderPlatformList(platformsData);
    } catch (error) {
        platformListEle.innerHTML = `<div class="error-message">Failed to load registry: ${error.message}</div>`;
    }
}

function renderPlatformList(platforms, filterText = '') {
    const container = document.getElementById('platform-list');
    container.innerHTML = '';

    const filter = filterText.toLowerCase();

    Object.entries(platforms).forEach(([key, data]) => {
        if (filter && !key.toLowerCase().includes(filter) && !data.description.toLowerCase().includes(filter)) {
            return;
        }

        const div = document.createElement('div');
        div.className = 'platform-item';
        div.onclick = () => selectPlatform(key, data, div);

        div.innerHTML = `
      <h3>${key}</h3>
      <p>${data.description}</p>
    `;

        container.appendChild(div);
    });
}

function filterPlatforms(text) {
    renderPlatformList(platformsData, text);
}

async function selectPlatform(platformKey, data, element) {
    // Update active state
    document.querySelectorAll('.platform-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');

    const previewArea = document.getElementById('tree-preview');
    previewArea.innerHTML = `
    <div class="platform-header">
      <h2>${platformKey} Index</h2>
      <p>Loading semantic tree representation...</p>
    </div>
    <div class="loader"></div>
  `;

    try {
        // Attempt to load `latest.json` for the platform
        const url = `${BASE_URL}/indices/${platformKey}/latest.json`;
        const fallbackUrl = `../indices/${platformKey}/latest.json`;

        let res = await fetch(url);
        if (!res.ok) {
            res = await fetch(fallbackUrl);
        }

        let indexData;
        if (!res.ok) {
            // Mock data for platforms not yet generated but in registry
            indexData = {
                meta: { version: "pending" },
                tree: { root: { title: `${platformKey} Root`, summary: `${platformKey} has not been indexed yet. The underlying index JSON could not be found.`, children: [] } }
            };
        } else {
            const text = await res.text();
            try {
                indexData = JSON.parse(text);
            } catch (e) {
                indexData = {
                    meta: { version: "pending" },
                    tree: { root: { title: `${platformKey} Root`, summary: `Failed to parse tree data for ${platformKey}.`, children: [] } }
                };
            }
        }

        renderTree(platformKey, indexData);
    } catch (error) {
        previewArea.innerHTML = `
      <div class="platform-header"><h2>${platformKey}</h2></div>
      <div class="error-message">Failed to load index tree. Ensure TreeHub has indexed this platform.</div>
    `;
    }
}

function renderTree(platformKey, data) {
    const container = document.getElementById('tree-preview');

    const headerHtml = `
    <div class="platform-header">
      <h2>${platformKey} Index</h2>
      <p>Version: <code>${data.meta.version || 'unknown'}</code> | Indexed At: <code>${data.meta.indexed_at || 'unknown'}</code></p>
    </div>
    <div class="tree-container" id="tree-root"></div>
  `;

    container.innerHTML = headerHtml;

    const rootElement = document.getElementById('tree-root');
    rootElement.appendChild(createNodeElement(data.tree.root, true));
}

function createNodeElement(node, isRoot = false) {
    const hasChildren = node.children && node.children.length > 0;
    const nodeDiv = document.createElement('div');
    nodeDiv.className = 'tree-node';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'node-content';

    const toggleBtn = document.createElement('button');
    toggleBtn.className = `node-toggle ${hasChildren ? '' : 'leaf'} ${isRoot ? 'expanded' : ''}`;
    toggleBtn.innerHTML = '▶';

    const infoText = document.createElement('div');
    infoText.className = 'node-info-text';
    infoText.innerHTML = `
    <div class="node-title">${node.title}</div>
    <div class="node-summary">${node.summary || ''}</div>
  `;

    contentDiv.appendChild(toggleBtn);
    contentDiv.appendChild(infoText);
    nodeDiv.appendChild(contentDiv);

    if (hasChildren) {
        const childrenContainer = document.createElement('div');
        childrenContainer.className = `node-children ${isRoot ? 'expanded' : ''}`;

        node.children.forEach(child => {
            childrenContainer.appendChild(createNodeElement(child));
        });

        nodeDiv.appendChild(childrenContainer);

        contentDiv.onclick = () => {
            toggleBtn.classList.toggle('expanded');
            childrenContainer.classList.toggle('expanded');
        };
    }

    return nodeDiv;
}
