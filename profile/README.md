# baskingspot

Zig is cold-blooded. Come bask.

The libraries between `std` and your application: the parts that std stops short of and every project ends up rewriting. Each one is a Zig 0.16 package that does one job and documents it.

## The lamps

- [**stdx**](https://github.com/mattrobenolt/stdx): extensions to the standard library. Fixed-capacity containers, strict parsers, IPv4 types, and the primitives std lacks.
- [**ztls**](https://github.com/mattrobenolt/ztls): TLS 1.3 that does no I/O. You feed it the bytes you read, and it returns the bytes to write. Pre-alpha.
- [**zcompress**](https://github.com/mattrobenolt/zcompress): Snappy, DEFLATE, gzip, zlib, and zstd in one module, with a namespace per codec.
- [**zig-benchmark**](https://github.com/mattrobenolt/zig-benchmark): Go-style benchmarks. Call `b.loop()` and get `ns/op`, allocation counts, and `benchstat` output.
- [**ztest**](https://github.com/mattrobenolt/ztest): a test runner that writes plain text to stderr instead of a TUI.
