#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const failures = [];
const passes = [];

function read(rel) {
  return fs.readFileSync(path.join(root, rel), 'utf8');
}

function pass(message) {
  passes.push(message);
}

function fail(message) {
  failures.push(message);
}

function walk(dir, predicate, output = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, predicate, output);
    if (entry.isFile() && predicate(full)) output.push(full);
  }
  return output;
}

function parseSimpleYaml(text) {
  const rootObject = {};
  const stack = [{ indent: -1, value: rootObject }];
  for (const rawLine of text.split(/\r?\n/)) {
    if (!rawLine.trim() || rawLine.trimStart().startsWith('#')) continue;
    const match = rawLine.match(/^(\s*)([A-Za-z0-9_-]+):(?:\s*(.*))?$/);
    if (!match) throw new Error(`Unsupported YAML line: ${rawLine}`);
    const indent = match[1].length;
    const key = match[2];
    let value = match[3] || '';
    while (stack.length && indent <= stack[stack.length - 1].indent) stack.pop();
    const parent = stack[stack.length - 1].value;
    if (!value) {
      parent[key] = {};
      stack.push({ indent, value: parent[key] });
      continue;
    }
    value = value.trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    parent[key] = value;
  }
  return rootObject;
}

function checkMarkdownLinks() {
  const markdownFiles = walk(root, file => file.endsWith('.md'));
  const linkPattern = /\[[^\]]+\]\(([^)]+)\)/g;
  for (const file of markdownFiles) {
    const text = fs.readFileSync(file, 'utf8');
    for (const match of text.matchAll(linkPattern)) {
      const target = match[1];
      if (/^[a-z]+:\/\//i.test(target) || target.startsWith('#')) continue;
      const targetPath = path.resolve(path.dirname(file), target.split('#')[0]);
      if (!fs.existsSync(targetPath)) fail(`Markdown link target missing in ${path.relative(root, file)}: ${target}`);
    }
  }
  pass('Markdown links resolved');
}

function checkOpenAiConfig() {
  let config;
  try {
    config = parseSimpleYaml(read('agents/openai.yaml'));
  } catch (err) {
    fail(`agents/openai.yaml parse failed: ${err.message}`);
    return;
  }
  const prompt = config.interface && config.interface.default_prompt;
  if (!prompt) fail('agents/openai.yaml is missing interface.default_prompt');
  if (/mermaid/i.test(prompt || '')) fail('agents/openai.yaml default_prompt still mentions Mermaid');
  if (!/excalidraw-style html diagram/i.test(prompt || '')) fail('agents/openai.yaml default_prompt does not point to Excalidraw-style HTML output');
  pass('OpenAI config parsed and points to HTML output');
}

function extractDiagramData(html) {
  const match = html.match(/const\s+DIAGRAM_DATA\s*=\s*(\{[\s\S]*?\n\});/);
  if (!match) throw new Error('DIAGRAM_DATA block missing');
  return Function(`"use strict"; return (${match[1].replace(/;$/, '')});`)();
}

function extractMetadata(html) {
  const match = html.match(/<script\s+type="application\/json"\s+id="agent-metadata">\s*([\s\S]*?)\s*<\/script>/i);
  if (!match) throw new Error('#agent-metadata JSON block missing');
  return JSON.parse(match[1]);
}

function checkTemplateSyntax(html) {
  let checked = 0;
  for (const match of html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/gi)) {
    const attrs = match[1];
    const body = match[2];
    if (/type=["']?importmap/i.test(attrs) || /application\/json/i.test(attrs)) continue;
    const source = body.replace(/^import rough from 'roughjs';\s*/m, '');
    try {
      Function(source);
      checked++;
    } catch (err) {
      fail(`Template runtime script syntax failed: ${err.message}`);
    }
  }
  if (checked < 1) fail('No runtime template scripts were checked');
  pass('Template JavaScript syntax parsed');
}

function validateDiagramContract(data, metadata) {
  const validConfidence = new Set(['observed', 'inferred', 'stated']);
  const validFidelity = new Set(['narrative-architecture', 'exact-code-graph', 'executive-concept-map']);
  const nodeIds = new Set();

  if (data.fidelity && !validFidelity.has(data.fidelity)) fail(`Invalid DIAGRAM_DATA.fidelity: ${data.fidelity}`);
  for (const field of ['audience', 'purpose', 'fidelity']) {
    if (data[field] && metadata[field] !== data[field]) fail(`#agent-metadata.${field} does not match DIAGRAM_DATA.${field}`);
  }

  for (const node of data.nodes || []) {
    if (!node.id) fail('A DIAGRAM_DATA node is missing id');
    if (nodeIds.has(node.id)) fail(`Duplicate DIAGRAM_DATA node id: ${node.id}`);
    nodeIds.add(node.id);
  }
  if (!nodeIds.size) fail('DIAGRAM_DATA has no nodes');

  for (const edge of data.edges || []) {
    const label = edge.label || 'unlabeled';
    if (!edge.label) fail(`Edge ${edge.sourceId || 'unknown'} -> ${edge.targetId || 'unknown'} is missing label`);
    if (!validConfidence.has(edge.confidence)) fail(`Edge "${label}" has invalid confidence: ${edge.confidence || 'missing'}`);
    if (!edge.evidence) fail(`Edge "${label}" is missing evidence`);
    if (!nodeIds.has(edge.sourceId)) fail(`Edge "${label}" has dangling source: ${edge.sourceId}`);
    if (!nodeIds.has(edge.targetId)) fail(`Edge "${label}" has dangling target: ${edge.targetId}`);
  }

  for (const cluster of data.clusters || []) {
    for (const id of cluster.nodeIds || []) {
      if (!nodeIds.has(id)) fail(`Cluster "${cluster.label || cluster.id}" references missing node: ${id}`);
    }
  }

  const metadataIds = new Set((metadata.entities || []).map(entity => entity.id));
  for (const id of nodeIds) {
    if (!metadataIds.has(id)) fail(`#agent-metadata.entities is missing DIAGRAM_DATA node id: ${id}`);
  }
  for (const entity of metadata.entities || []) {
    if (!nodeIds.has(entity.id)) fail(`#agent-metadata.entities references missing DIAGRAM_DATA node id: ${entity.id}`);
  }
  for (const rel of metadata.relationships || []) {
    const label = rel.label || 'unlabeled';
    if (!rel.label) fail(`Metadata relationship ${rel.sourceId || 'unknown'} -> ${rel.targetId || 'unknown'} is missing label`);
    if (!validConfidence.has(rel.confidence)) fail(`Metadata relationship "${label}" has invalid confidence: ${rel.confidence || 'missing'}`);
    if (!rel.evidence) fail(`Metadata relationship "${label}" is missing evidence`);
    if (!nodeIds.has(rel.sourceId)) fail(`Metadata relationship "${label}" has dangling source: ${rel.sourceId}`);
    if (!nodeIds.has(rel.targetId)) fail(`Metadata relationship "${label}" has dangling target: ${rel.targetId}`);
  }

  pass('DIAGRAM_DATA and #agent-metadata contract validated');
}

function checkTemplate() {
  const html = read('assets/html-excalidraw-template.html');
  checkTemplateSyntax(html);
  let data;
  let metadata;
  try {
    data = extractDiagramData(html);
    pass('DIAGRAM_DATA parsed');
  } catch (err) {
    fail(`DIAGRAM_DATA parse failed: ${err.message}`);
  }
  try {
    metadata = extractMetadata(html);
    pass('#agent-metadata JSON parsed');
  } catch (err) {
    fail(`#agent-metadata parse failed: ${err.message}`);
  }
  if (data && metadata) validateDiagramContract(data, metadata);
}

checkMarkdownLinks();
checkOpenAiConfig();
checkTemplate();

if (failures.length) {
  console.error('create-diagram validation failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('create-diagram validation passed:');
for (const message of passes) console.log(`- ${message}`);
