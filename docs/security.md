# Security and Vulnerability Management

## Trivy Image Scanning

Trivy is integrated into the Jenkins CI pipeline to automatically scan the
application Docker images for HIGH and CRITICAL vulnerabilities.

The following images are scanned:

- Nginx
- WordPress
- PrestaShop

The scan currently operates in report-only mode. Security findings are reported
by the pipeline but do not automatically fail the build.

## Vulnerability Remediation

During the initial security scan, Trivy detected CRITICAL vulnerabilities in
the PrestaShop image, including vulnerabilities originating from Debian system
packages and application dependencies.

As a remediation step, the PrestaShop Docker image was hardened by updating
available operating system packages during the image build.

After rebuilding and rescanning the image, the fixable CRITICAL findings from
the outdated Debian packages were removed.

## Remaining Findings

The rescan still reports CRITICAL findings in dependencies bundled with the
PrestaShop 8.1.7 application, including:

- `phpoffice/phpspreadsheet`
- `prestashop/ps_facetedsearch`
- `symfony/symfony`
- `twig/twig`

These dependencies are managed as part of the PrestaShop application stack.
Updating them independently without compatibility and regression testing could
introduce breaking changes or application instability.

For this reason, the remaining findings are currently documented as known
security risks rather than being upgraded blindly.

## Risk Management

The current approach is:

1. Detect HIGH and CRITICAL vulnerabilities automatically with Trivy.
2. Remediate vulnerabilities that can be safely fixed at the image/OS level.
3. Rebuild and rescan the affected image after remediation.
4. Document remaining application-level findings.
5. Upgrade application dependencies only after compatibility and regression
   testing.

A future improvement would be to introduce a stricter CI security gate once
the remaining application dependencies have been upgraded and validated.
