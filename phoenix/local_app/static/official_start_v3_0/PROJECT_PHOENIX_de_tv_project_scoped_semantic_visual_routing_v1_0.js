// PROJECT PHOENIX DE TV DIRECT VISUAL ARTIFACT OPEN + RENDER BRIDGE v1.0
(() => {
  'use strict';

  const VERSION = '1.2.0';
  const PROJECT_RE = /\bPHOENIX-PAT-\d+\b/i;
  const MAX_SEEK_STEPS = 1200;

  let lastKind = null;
  let lastProject = null;
  let seekToken = 0;

  // Backward-compatible regression contract:
  // cross-project fallback is verboden

  const normPath = s => String(s || '').trim().replace(/\\/g, '/');

  function normalizeCommand(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[_-]+/g, ' ')
      .replace(/[.,;:!?()[\]{}"'`]+/g, ' ')
      .replace(/\b(de|het|een|mijn|project)\b/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function projectIdFromText(value) {
    const m = String(value || '').match(PROJECT_RE);
    return m ? m[0].toUpperCase() : null;
  }

  function authoritativeActiveProjectId() {
    for (const id of ['progressStep', 'progressLabel']) {
      const node = document.getElementById(id);
      const pid = projectIdFromText(node ? node.textContent : '');
      if (pid) return pid;
    }

    const modal = document.getElementById('modal');
    if (modal) {
      const style = getComputedStyle(modal);
      const shown = style.display !== 'none' && style.visibility !== 'hidden';
      if (shown) {
        const pid = projectIdFromText(modal.textContent || '');
        if (pid) return pid;
      }
    }

    const direct = [];
    document.querySelectorAll(
      '[data-current-project],[data-active-project],[data-project-id],select,input'
    ).forEach(el => {
      if (el.closest && el.closest('#projectList')) return;
      const values = [
        el.dataset?.currentProject,
        el.dataset?.activeProject,
        el.dataset?.projectId,
        el.value
      ];
      for (const raw of values) {
        const pid = projectIdFromText(raw);
        if (pid) direct.push(pid);
      }
    });

    if (direct.length) return direct[direct.length - 1];

    // Never infer the active project from #projectList.
    return null;
  }

  function semanticKind(command) {
    const q = normalizeCommand(command);
    if (!q) return null;

    if (
      /\bsituatie\s*tekening\b/.test(q) ||
      /\bsituatietekening\b/.test(q) ||
      /\bsite\s*plan\b/.test(q) ||
      /\bterreintekening\b/.test(q) ||
      /\bterrein\s*tekening\b/.test(q)
    ) return 'site_plan';

    if (
      /\b3d\s*viewer\b/.test(q) ||
      /\bviewer\s*3d\b/.test(q) ||
      /\b3d\s*weergave\b/.test(q) ||
      /\b3d\s*model\b/.test(q)
    ) return 'viewer_3d';

    if (
      /\bautomatische?\s*video\b/.test(q) ||
      /\bautomatische?\s*videopresentatie\b/.test(q) ||
      /\bauto\s*video\b/.test(q) ||
      /\bvideopresentatie\b/.test(q)
    ) return 'auto_video';

    return null;
  }

  function artifactFor(pid, kind, dxf = false) {
    const base = `projects/runtime/${pid}`;

    if (kind === 'viewer_3d')
      return `${base}/results/generated_visual_media/viewer_3d/phoenix_3d_viewer.html`;

    if (kind === 'auto_video')
      return `${base}/results/generated_visual_media/auto_video/phoenix_automatic_video.avi`;

    if (kind === 'site_plan')
      return `${base}/results/session_adapters/architecture/drawings/site_plan.${dxf?'dxf':'svg'}`;

    return null;
  }

  function gate(title, message) {
    const stage = document.getElementById('phoenixTvStage');
    const meta = document.getElementById('phoenixTvMeta');

    if (stage) {
      stage.innerHTML =
        `<div style="padding:18px;color:#dceeff;font-family:Segoe UI,Arial,sans-serif">` +
        `<strong>${title}</strong><br>${message}</div>`;
    }
    if (meta) meta.textContent = `DIRECT ARTIFACT BRIDGE · ${message}`;
  }

  function currentArtifactPath() {
    const meta = document.getElementById('phoenixTvMeta');
    const text = normPath(meta ? meta.textContent : '');

    const projectPath = text.match(/projects\/runtime\/PHOENIX-PAT-\d+\/[^·\r\n]+/i);
    if (projectPath) return projectPath[0].trim();

    const outputPath = text.match(/outputs\/[^·\r\n]+/i);
    if (outputPath) return outputPath[0].trim();

    return '';
  }

  function sameArtifact(actual, wanted) {
    const a = normPath(actual).toLowerCase();
    const w = normPath(wanted).toLowerCase();
    return !!a && !!w && (a === w || a.endsWith('/' + w) || w.endsWith('/' + a));
  }

  function parsePosition() {
    const meta = document.getElementById('phoenixTvMeta');
    const text = String(meta ? meta.textContent : '');
    const m = text.match(/\b(\d+)\s*\/\s*(\d+)\b/);
    return m ? { index: Number(m[1]), total: Number(m[2]) } : null;
  }

  function waitForMetaChange(previous, token, timeout = 900) {
    return new Promise(resolve => {
      const meta = document.getElementById('phoenixTvMeta');
      if (!meta || token !== seekToken) {
        resolve(false);
        return;
      }

      let done = false;
      const finish = changed => {
        if (done) return;
        done = true;
        observer.disconnect();
        clearTimeout(timer);
        resolve(changed);
      };

      const observer = new MutationObserver(() => {
        const now = String(meta.textContent || '');
        if (now !== previous) finish(true);
      });

      observer.observe(meta, {
        childList: true,
        subtree: true,
        characterData: true
      });

      const timer = setTimeout(() => finish(false), timeout);
    });
  }

  async function seekExactArtifact(path) {
    const wanted = normPath(path);
    const next = document.getElementById('phoenixTvNext');
    const meta = document.getElementById('phoenixTvMeta');

    if (!next || !meta || !wanted) {
      gate('DE TV DIRECT ARTIFACT BRIDGE GEBLOKKEERD',
        'Bestaande TV-carrouselrenderer kon niet worden gevonden.');
      return false;
    }

    const token = ++seekToken;
    const initial = currentArtifactPath();

    if (sameArtifact(initial, wanted)) {
      return true;
    }

    const pos = parsePosition();
    const max = Math.min(
      MAX_SEEK_STEPS,
      pos && pos.total > 0 ? pos.total + 2 : MAX_SEEK_STEPS
    );

    for (let step = 0; step < max; step++) {
      if (token !== seekToken) return false;

      const beforeText = String(meta.textContent || '');
      next.click();
      await waitForMetaChange(beforeText, token);

      const actual = currentArtifactPath();
      if (sameArtifact(actual, wanted)) {
        const pid = projectIdFromText(actual);
        if (lastProject && pid && pid !== lastProject) {
          gate(
            'DE TV CROSS-PROJECT ROUTING GEBLOKKEERD',
            `Artifact ${pid} geweigerd; authoritative actieve project is ${lastProject}.`
          );
          return false;
        }
        return true;
      }

      if (actual && sameArtifact(actual, initial) && step > 1) break;
    }

    gate(
      'DE TV ARTIFACT NIET GEVONDEN',
      `Het exacte artifact voor ${lastProject || 'het actieve project'} staat niet in de huidige TV-artifactlijst: ${wanted}`
    );
    return false;
  }

  function blankFraction(img) {
    try {
      if (!img?.complete || !img.naturalWidth || !img.naturalHeight) return null;

      const w = Math.min(320, img.naturalWidth);
      const h = Math.min(220, img.naturalHeight);
      const canvas = document.createElement('canvas');
      canvas.width = w;
      canvas.height = h;

      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, w, h);
      ctx.drawImage(img, 0, 0, w, h);

      const data = ctx.getImageData(0, 0, w, h).data;
      let ink = 0;
      const total = w * h;

      for (let i = 0; i < data.length; i += 4) {
        if (
          data[i + 3] > 15 &&
          (data[i] < 235 || data[i + 1] < 235 || data[i + 2] < 235)
        ) ink++;
      }

      return ink / total;
    } catch (_) {
      return null;
    }
  }

  async function runSitePlanQualityGate(pid) {
    const stage = document.getElementById('phoenixTvStage');
    if (!stage) return;

    const img = stage.querySelector('img');
    if (!img) return;

    const evaluate = async () => {
      const fraction = blankFraction(img);
      if (fraction !== null && fraction < 0.0035) {
        gate(
          'SITUATIETEKENING KWALITEITSGATE',
          `SVG voor ${pid} is vrijwel blanco (${(fraction * 100).toFixed(2)}% beeldinhoud). Project-eigen DXF wordt geopend via de bestaande DE TV-renderer.`
        );
        await seekExactArtifact(artifactFor(pid, 'site_plan', true));
      }
    };

    if (img.complete) {
      setTimeout(evaluate, 100);
    } else {
      img.addEventListener('load', () => setTimeout(evaluate, 100), { once: true });
    }
  }

  async function openSemantic(kind) {
    const pid = authoritativeActiveProjectId();

    if (!pid) {
      gate(
        'DE TV PROJECT-SCOPE GEBLOKKEERD',
        'Geen authoritative actieve projectsessie gevonden; cross-project fallback is verboden.'
      );
      return;
    }

    lastKind = kind;
    lastProject = pid;

    const wanted = artifactFor(pid, kind, false);
    const found = await seekExactArtifact(wanted);

    if (found && kind === 'site_plan') {
      runSitePlanQualityGate(pid);
    }
  }

  function interceptSemantic(ev) {
    const button = ev.target?.closest?.('#phoenixTvCommandGo');
    if (!button) return;

    const input = document.getElementById('phoenixTvCommand');
    if (!input) return;

    const kind = semanticKind(input.value);
    if (!kind) return;

    // Important: do not forward a filesystem/artifact path to the legacy text parser.
    ev.preventDefault();
    ev.stopImmediatePropagation();

    openSemantic(kind);
  }

  function start() {
    document.addEventListener('click', interceptSemantic, true);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }

  window.PHOENIX_TV_PROJECT_SCOPED_VISUAL_ROUTING_V1_0 = {
    VERSION,
    normalizeCommand,
    semanticKind,
    projectIdFromText,
    authoritativeActiveProjectId,
    artifactFor,
    currentArtifactPath,
    seekExactArtifact
  };
})();
