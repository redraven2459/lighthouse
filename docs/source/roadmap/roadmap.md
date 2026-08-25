# Roadmap
Lighthouse is currently an 'early-access' project. Whilst most of the key functionality and core UI is available it is not currently provided with any guarantee of being bug-free.

I anticipate Lighthouse to go through three stages of development prior to a stable release being released.

## Stage 1: Functional completion (expected: early 2027)
Due to time constraints Lighthouse was primarily developed around my immediate needs and experiences. The road to V0.1.0 has been littered with shortcomings that have been identified that will now be addressed.

See [Stage 1: Functional Completion](stage_1.md) for details about what this means for:

- Lighthouse-Server
- Lighthouse-Client
- Documentation

Upon Stage 1 completion Lighthouse will enter a feature-freeze. This will enable the entire development focus to shift towards the testing framework and stable release of Lighthouse.

## Stage 2: Testing framework (expected: late 2027)
A testing framework is an essential part of any publicly available software package. Whilst forgoing tests is an acceptable trade-off during 'early-access' where development is more turbulent I am committed to making Lighthouse a reliably-reliable piece of software.

The testing framework will consist of:

- Github Actions to ensure all contributions to 'main' contain appropriate tests and successfully pass all available tests.
- Lighthouse-Server's test suite
- Lighthouse-Client's test suite
- A combined Lighthouse-Server and Lighthouse-Client integration test package (potentially: subject to perceived benefit vs engineering effort).

## Stage 3: Release candidates (baseline: V1.0.0, expected: 2028)
During the lead up to V1.0.0 Lighthouse will adopt a monthly release candidate cycle. Any issues that are identified as being Lighthouse-induced and undesirable will be prioritised for the next release candidate window. Lighthouse will not release as V1.0.0 until three consecutive release candidate windows have passed without problem.

## Post release development
🥳 If we get this far I'll be having a rum and some time away!

In all seriousness, the feature-freeze will be lifted and any community feature-based pull and/or feature requests will be considered for incorporating. Whilst development will likely slow if there's any ideas floating around please reach out.
