// Used by brand.py. Keeps the <!--! grid --> comments (svgo keeps comments
// that start with "!") and the favicon's prefers-color-scheme rule, which
// inlineStyles would drop.
export default {
  multipass: true,
  js2svg: { pretty: true, indent: 2, eol: "lf", finalNewline: true },
  plugins: [
    {
      name: "preset-default",
      params: {
        overrides: {
          inlineStyles: false,
          minifyStyles: false,
          cleanupNumericValues: { floatPrecision: 2 },
          convertPathData: { floatPrecision: 1 },
        },
      },
    },
  ],
};
