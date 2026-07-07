%%%
title = 'Sample Spec - Volume 2 - Editor Copy'
abbrev = "sample"
ipr = "none"

[seriesInfo]
name = "Internet-Draft"
value = "sample"
status = "standard"
stream = "independent"
%%%

.# Abstract

This abstract must be dropped from the ISO Word output.

## Notice

This frontmatter subsection comes after the abstract and MUST survive: mmark
ends the abstract at the next heading of any level.

{mainmatter}

.# Foreword

Foreword text (unnumbered in both renditions).

# Scope

A normative example follows and must pass through verbatim:

```
%%%
title = "not the real title"
%%%
{mainmatter}
.# This dot-hash line is example content, not a heading
{: title="keep me"}
```

Body continues after the example.

{: .stray-attribute-list}

{backmatter}

# Bibliography

[1] Some reference.
