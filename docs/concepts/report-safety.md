---
title: Report safety
description: Why an HTML report can't load anything, run injected code or be broken by hostile model output, and how to share one safely.
---

# Report safety

A report embeds model outputs, and model outputs can be hostile: an answer can contain `</script><script>…`, an
image tag with an error handler, or text that looks like a template placeholder. Reports are also meant to be shared.
So they are built to be inert.

- **Offline.** CSS and JavaScript are inlined. No CDN, font, image or telemetry URL is referenced. Fonts are the
  system's.
- **Locked by Content Security Policy.** The page declares `default-src 'none'`, `connect-src 'none'`,
  `base-uri 'none'`, `form-action 'none'` and `img-src data:`. The inline script and stylesheet are allowed **only by
  their SHA-256 hashes**, with no `unsafe-inline`. Even if markup were injected, it couldn't run a script, load a
  resource or send data anywhere.
- **Data stays data.** The run is embedded as JSON in `<script type="application/json">`, with `<`, `>`, `&` and the
  U+2028/U+2029 line separators escaped, so evaluated text can't close the script element. The template is filled in
  one pass, so text that looks like a placeholder is never substituted.
- **Text stays text.** The page builds every element with DOM calls and sets untrusted strings with `textContent`.
  It uses no `innerHTML`, no `eval`, no network calls and no browser storage. Tests check all of this, including a
  hostile sample whose input contains a script tag, an `<img onerror>`, a placeholder and a line separator.
- **Bounded.** Any text field longer than 6,000 characters is shortened in the page (the full text stays in `run.json`).
- **Shareable.** The `public` profile removes inputs, outputs, references, explanations, the dataset path and the git
  revision, leaving the numbers ([Reports](../guides/reports.md#profiles)).
- **Traceable.** A manifest is embedded in the page (`guage-kit/report-manifest@1`): renderer, Guage Kit and Ananke
  versions, run id, dataset fingerprint, a SHA-256 digest of the embedded data, the profile and its limitations.

Opening a report runs no command and contacts no server.
