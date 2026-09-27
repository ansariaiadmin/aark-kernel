import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";

export default [
  // Global ignores must come first and must not be combined with rules,
  // otherwise the patterns are treated as per-file overrides.
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      ".next/**",
      "coverage/**",
      "out/**",
      "next-env.d.ts",
      "**/*.tsbuildinfo",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    // CommonJS build/tooling configs legitimately use `module.exports`.
    // Linting them as ESM produced "'module' is not defined" (no-undef) and
    // failed CI even though the files are correct.
    files: ["*.config.js", "*.config.cjs", "postcss.config.js", "tailwind.config.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "commonjs",
      globals: { ...globals.node },
    },
  },
  {
    // ESM build configs (next.config.mjs) run in Node, not the browser.
    files: ["**/*.mjs", "**/*.cjs"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: { ...globals.node },
    },
  },
  {
    files: ["**/*.ts", "**/*.tsx"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: { ...globals.browser },
    },
    rules: {
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      // NOTE: `react-hooks/exhaustive-deps` was listed here but
      // eslint-plugin-react-hooks is not a dependency, so ESLint 9 aborted with
      // "Definition for rule ... was not found". Either install the plugin or
      // don't reference it — the project currently does not use it.,
    },
  },
];
