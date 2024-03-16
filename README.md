# Limuloid

**L**i**m**u**l**oi**d** is a tool to help **LLM**s conform to XML **DTD**s.
With the help of Limuloid, you can be 100% certain that your LLM output will be
machine-parsable and conformant to a given schema, no matter how complex.

## Usage

To use Limuloid, you must first already have an XML schema. Limuloid only
works with DTDs, but if you have a schema in the XSD or Relax-NG formats, there
are many tools out there which will convert those formats into a DTD.

Limuloid takes the DTD as input and outputs a GBNF file that can be consumed by
llama.cpp. So you would generate a GBNF file with Limuloid by running
`./limuloid.py < my_file.dtd > my_file.gbnf` and then you would pass that file
to llama.cpp by running `llama.cpp/main --grammar-file my_file.gbnf ...`.

```
usage: limuloid.py [-h] [-i DTD_POINTER] [-o OUTPUT_BUFFER]
[--allow-comments | --no-allow-comments] [--allow-pi | --no-allow-pi]
[--allow-cdata | --no-allow-cdata] [--xml-header {REQUIRED,ALLOWED,FORBIDDEN}]
[--doctype {REQUIRED,ALLOWED,FORBIDDEN}]

options:
  -h, --help            show this help message and exit
  -i DTD_POINTER, --input DTD_POINTER
                        Input DTD file (default STDIN)
  -o OUTPUT_BUFFER, --output OUTPUT_BUFFER
                        GBNF output location (default STDOUT)
  --allow-comments, --no-allow-comments
                        Whether to allow comments in the generated XML
			(default False)
  --allow-pi, --no-allow-pi
                        Whether to allow XML processing instructions in the
			generated XML (default False)
  --allow-cdata, --no-allow-cdata
                        Whether to allow CData sections in the generated XML
			(default True)
  --xml-header {REQUIRED,ALLOWED,FORBIDDEN}
                        Whether to include an XML header in the generated XML
			(default ALLOWED)
  --doctype {REQUIRED,ALLOWED,FORBIDDEN}
                        Whether to include a DOCTYPE declaration in the
			generated XML (default REQUIRED)
```

## Tips

While the grammar file constrains the LLM output to conform to the given
grammar, the model is not aware of this constraint. If the model is not
otherwise informed it should be producing XML, either through training data or
the prompt, then it will be fighting the grammar file and not producing much
output. It's essential to give a prompt which says to output XML, and it
probably is beneficial to include the DTD in the prompt.

The error handling in the llama.cpp grammar file functionality is pretty minimal
and most of the time it just segfaults. This could be an error in the grammar
file that Limuloid is generating, or it could be an error in the DTD which you
provided. Currently, neither Limuloid  nor llama.cpp will raise an error ahead
of time if your DTD refers to an element or attribute that is not later defined.
Llama.cpp will just segfault while running.

## Development

At present this is just a one-man hobby script. Already the script is capable
of converting the W3C's XHTML 1.0 DTD into a valid GBNF file.
There are still features to add and undoubtedly bugs to squash. PRs are welcome.

## Name??

> limuloid: Any horseshoe crab of the superfamily Limuloidea

I ran a Scrabble word search with LLMDTD and this is the best it came up with.
No prior hits on Github!
