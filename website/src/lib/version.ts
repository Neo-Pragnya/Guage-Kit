// The package version, read from src/guage_kit/version.py when the site is built (the build runs in website/).
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const source = readFileSync(resolve(process.cwd(), "../src/guage_kit/version.py"), "utf-8");
const match = source.match(/__version__\s*=\s*"([^"]+)"/);
if (!match) throw new Error("cannot read __version__ from src/guage_kit/version.py");

export const VERSION: string = match[1];
export const PYPI_URL = "https://pypi.org/project/guage-kit/";
export const PYPI_RELEASE_URL = `${PYPI_URL}${VERSION}/`;
