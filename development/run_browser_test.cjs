const path = require("path");
const { chromium } = require("playwright");
if (process.env.GENESIS_TEST_CHROMIUM) {
  const launch = chromium.launch.bind(chromium);
  chromium.launch = options => launch({ ...options, executablePath: process.env.GENESIS_TEST_CHROMIUM });
}
const file = path.resolve(process.argv[2]);
process.argv = [process.argv[0], file, ...process.argv.slice(3)];
require(file);
