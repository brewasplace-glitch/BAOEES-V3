// PROJECT PHOENIX DE TV AUTHORITATIVE ACTIVE PROJECT CONTEXT + COMMAND NORMALIZATION v1.0 R1
(() => {
  'use strict';

  const VERSION = '1.1.1';
  const PROJECT_RE = /\bPHOENIX-PAT-\d+\b/i;
  let busy = false;
  let lastKind = null;
  let lastProject = null;

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
    // 1. Current orchestrator progress is authoritative.
    for (const id of ['progressStep', 'progressLabel']) {
      const node = document.getElementById(id);
      const pid = projectIdFromText(node ? node.textContent : '');
      if (pid) return pid;
    }

    // 2. Visible active session/result modal is authoritative.
    const modal = document.getElementById('modal');
    if (modal) {
      const style = getComputedStyle(modal);
      const shown = style.display !== 'none' && style.visibility !== 'hidden';
      if (shown) {
        const pid = projectIdFromText(modal.textContent || '');
        if (pid) return pid;
      }
    }

    // 3. Explicit current-project controls, but never catalog entries.
    const direct = [];
    document.querySelectorAll(
      '[data-current-project],[data-active-project],[data-project-id],select,input'
    ).forEach(el => {
      if (el.closest && el.closest('#projectList')) return;
      const vals = [
        el.dataset?.currentProject,
        el.dataset?.activeProject,
        el.dataset?.projectId,
        el.value
      ];
      for (const raw of vals) {
        const pid = projectIdFromText(raw);
        if (pid) direct.push(pid);
      }
    });
    if (direct.length) return direct[direct.length - 1];

    // 4. Never infer the active project from #projectList.
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

    if (kind === 'viewer_3d') {
      return `${base}/results/generated_visual_media/viewer_3d/phoenix_3d_viewer.html`;
    }

    if (kind === 'auto_video') {
      return `${base}/results/generated_visual_media/auto_video/phoenix_automatic_video.avi`;
    }

    if (kind === 'site_plan') {
      // Keep this exact expression for backward-compatible regression contract:
      return `${base}/results/session_adapters/architecture/drawings/site_plan.${dxf?'dxf':'svg'}`;
    }

    return null;
  }

  function gate(title, msg) {
    const stage = document.getElementById('phoenixTvStage');
    const meta = document.getElementById('phoenixTvMeta');
    if (stage) {
      stage.innerHTML =
        `<div style="padding:18px;color:#dceeff"><strong>${title}</strong><br>${msg}</div>`;
    }
    if (meta) {
      meta.textContent = `PROJECT-SCOPED QUALITY GATE · ${msg}`;
    }
  }

  function submit(path) {
    if (busy || !path) return false;

    const input = document.getElementById('phoenixTvCommand');
    const button = document.getElementById('phoenixTvCommandGo');
    if (!input || !button) return false;

    busy = true;
    input.value = `toon ${path}`;

    setTimeout(() => {
      button.click();
      setTimeout(() => {
        busy = false;
      }, 700);
    }, 20);

    return true;
  }

  function interceptSemantic(ev) {
    if (busy) return;

    const button = ev.target?.closest?.('#phoenixTvCommandGo');
    if (!button) return;

    const input = document.getElementById('phoenixTvCommand');
    if (!input) return;

    const kind = semanticKind(input.value);
    if (!kind) return;

    const pid = authoritativeActiveProjectId();

    ev.preventDefault();
    ev.stopImmediatePropagation();

    if (!pid) {
      gate(
        'DE TV PROJECT-SCOPE GEBLOKKEERD',
        'Geen authoritative actieve projectsessie gevonden; cross-project fallback is verboden.'
      );
      return;
    }

    lastKind = kind;
    lastProject = pid;
    submit(artifactFor(pid, kind, false));
  }

  function metaArtifact() {
    const meta = document.getElementById('phoenixTvMeta');
    const text = normPath(meta?.textContent);
    const m = text.match(/projects\/runtime\/(PHOENIX-PAT-\d+)\/[^·\s]+/i);
    return m ? { path: m[0], pid: m[1].toUpperCase() } : null;
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
        ) {
          ink++;
        }
      }

      return ink / total;
    } catch (_) {
      return null;
    }
  }

  function postRouteCheck() {
    if (!lastProject || busy) return;

    const authoritative = authoritativeActiveProjectId();
    if (authoritative && authoritative !== lastProject) {
      lastProject = authoritative;
      submit(artifactFor(lastProject, lastKind, false));
      return;
    }

    const artifact = metaArtifact();
    if (artifact && artifact.pid !== lastProject) {
      gate(
        'DE TV CROSS-PROJECT ROUTING GEBLOKKEERD',
        `Artifact ${artifact.pid} geweigerd; authoritative actieve project is ${lastProject}.`
      );
      setTimeout(() => submit(artifactFor(lastProject, lastKind, false)), 50);
      return;
    }

    if (lastKind === 'site_plan') {
      const img = document.getElementById('phoenixTvStage')?.querySelector('img');
      if (!img) return;

      const run = () => {
        const fraction = blankFraction(img);
        if (fraction !== null && fraction < 0.0035) {
          gate(
            'SITUATIETEKENING KWALITEITSGATE',
            `SVG voor ${lastProject} is vrijwel blanco (${(fraction * 100).toFixed(2)}% beeldinhoud). Project-eigen DXF wordt geopend.`
          );
          setTimeout(
            () => submit(artifactFor(lastProject, 'site_plan', true)),
            80
          );
        }
      };

      if (img.complete) {
        setTimeout(run, 80);
      } else {
        img.addEventListener('load', () => setTimeout(run, 80), { once: true });
      }
    }
  }

  function start() {
    document.addEventListener('click', interceptSemantic, true);

    const observer = new MutationObserver(postRouteCheck);
    const stage = document.getElementById('phoenixTvStage');
    const meta = document.getElementById('phoenixTvMeta');
    const progressStep = document.getElementById('progressStep');
    const progressLabel = document.getElementById('progressLabel');

    if (stage) {
      observer.observe(stage, {
        childList: true,
        subtree: true,
        characterData: true,
        attributes: true
      });
    }

    if (meta) {
      observer.observe(meta, {
        childList: true,
        subtree: true,
        characterData: true
      });
    }

    if (progressStep) {
      observer.observe(progressStep, {
        childList: true,
        subtree: true,
        characterData: true
      });
    }

    if (progressLabel) {
      observer.observe(progressLabel, {
        childList: true,
        subtree: true,
        characterData: true
      });
    }
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
    artifactFor
  };
})();
