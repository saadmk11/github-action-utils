const { spawnSync } = require("node:child_process");
const path = require("node:path");

// The runner supplies STATE_* values to each new hook process.
module.exports = (phase) => {
  const result = spawnSync(
    "python",
    [path.join(__dirname, "check_state.py"), phase],
    { stdio: "inherit" },
  );
  if (result.error) throw result.error;
  process.exit(result.status === null ? 1 : result.status);
};
