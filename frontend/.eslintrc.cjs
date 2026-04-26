module.exports = {
  root: true,
  env: {
    browser: true,
    es2023: true,
    node: true,
  },
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: { jsx: true },
  },
  settings: { react: { version: 'detect' } },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
    'plugin:storybook/recommended',
  ],
  plugins: ['react', 'react-hooks', 'react-refresh'],
  ignorePatterns: [
    'dist/',
    'node_modules/',
    'coverage/',
    'storybook-static/',
    'src/api/generated/**',
    'src/api/index.ts',
    'src/pages/daily-log/refactor_feed.js',
  ],
  overrides: [
    {
      files: ['src/components/TaskContractForm.jsx'],
      rules: {
        'no-unused-vars': [
          'error',
          {
            argsIgnorePattern: '^_',
            varsIgnorePattern: '^_|^useEffect$',
            caughtErrorsIgnorePattern: '^_',
            ignoreRestSiblings: true,
          },
        ],
      },
    },
    {
      files: ['src/components/attachments/AttachmentEvidenceViewer.jsx'],
      rules: {
        'no-unused-vars': [
          'error',
          {
            argsIgnorePattern: '^_',
            varsIgnorePattern: '^_|^Info$',
            caughtErrorsIgnorePattern: '^_',
            ignoreRestSiblings: true,
          },
        ],
      },
    },
    {
      files: ['src/pages/RemoteReviewDashboard.jsx'],
      rules: {
        'no-unused-vars': [
          'error',
          {
            argsIgnorePattern: '^_|^err$',
            varsIgnorePattern: '^_',
            caughtErrorsIgnorePattern: '^_|^err$',
            ignoreRestSiblings: true,
          },
        ],
      },
    },
  ],
  rules: {
    'react/react-in-jsx-scope': 'off',
    'react/prop-types': 'off',
    'react/jsx-no-target-blank': 'warn',
    'react-refresh/only-export-components': 'off',
    'no-empty': ['error', { allowEmptyCatch: true }],
    'no-case-declarations': 'off',
    'no-useless-escape': 'warn',
    'no-unused-vars': [
      'error',
      {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
        caughtErrorsIgnorePattern: '^_',
        ignoreRestSiblings: true,
      },
    ],
  },
}
