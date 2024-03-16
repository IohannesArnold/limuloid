#! /usr/bin/env python
# limuloid.py -- script to make LLMs conform to DTDs
# Copyright (C) John Arnold
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import argparse
import string
import sys
from enum import auto, Enum
from lxml import etree


class Usage(Enum):
    REQUIRED = auto()
    ALLOWED = auto()
    FORBIDDEN = auto()


def _sanatize_ident(ident_in):
    good_chars = [c for c in ident_in.casefold() if c in string.ascii_lowercase]
    return "".join(good_chars)


def _handle_element_content(
    allow_cdata, misc, output_buffer, content, indent_len, new_group=False
):
    if new_group:
        output_buffer.write(" " * indent_len)
        output_buffer.write("(\n")
        indent_len += 2
        output_buffer.write(" " * indent_len)
        output_buffer.write(f"({ ' | '.join(misc) })*\n")
    if content.type == "element":
        output_buffer.write(" " * indent_len)
        output_buffer.write(f"element-{_sanatize_ident(content.name)}")
    elif content.type == "pcdata":
        output_buffer.write(" " * indent_len)
        ents = ["Reference"] + misc[1:]
        if allow_cdata:
            ents.append("CDSect")
        output_buffer.write(f"(CharData? (({ ' | '.join(ents) }) CharData?)*)")
    elif content.type == "seq":
        _handle_element_content(
            allow_cdata, misc, output_buffer, content.left, indent_len
        )
        output_buffer.write("\n")
        output_buffer.write(" " * indent_len)
        output_buffer.write(f"({ ' | '.join(misc) })*\n")
        _handle_element_content(
            allow_cdata,
            misc,
            output_buffer,
            content.right,
            indent_len,
            content.right.type == "or",
        )
    elif content.type == "or":
        _handle_element_content(
            allow_cdata,
            misc,
            output_buffer,
            content.left,
            indent_len,
            content.left.type == "seq",
        )
        output_buffer.write(" |\n")
        _handle_element_content(
            allow_cdata,
            misc,
            output_buffer,
            content.right,
            indent_len,
            content.right.type == "seq",
        )
    if new_group:
        output_buffer.write("\n")
        output_buffer.write(" " * indent_len)
        output_buffer.write(f"({ ' | '.join(misc) })*\n")
        indent_len -= 2
        output_buffer.write(" " * indent_len)
        output_buffer.write(")")
    if content.occur == "opt":
        output_buffer.write("?")
    elif content.occur == "mult":
        output_buffer.write("*")
    elif content.occur == "plus":
        output_buffer.write("+")


def create_grammar(
    dtd_pointer,
    output_buffer,
    allow_comments=False,
    allow_pi=False,
    allow_cdata=True,
    xml_header=Usage.ALLOWED,
    doctype=Usage.REQUIRED,
):

    if not isinstance(xml_header, Usage):
        xml_header = Usage[str(xml_header).upper()]

    if not isinstance(doctype, Usage):
        doctype = Usage[str(doctype).upper()]

    dtd = etree.DTD(dtd_pointer)

    misc = ["S"]
    root_element = None

    output_buffer.write(
        r"""# Character Range
# Diverges from the official spec by not including
# '-' (\x2D) '>' (\x3E) '?' (\x3F) ']' (\x5F)
# because the llama.cpp grammar is only additive, and in the official spec those
# chars are excluded elsewhere.
Char ::= "\x09" | "\x0A" | "\x0D" | [\x20-\x2C] | [\x2E-\x3D] | [\x40-\x5E] |
         [\x60-\uD7FF] | [\uE000-\uFFFD] | [\U00010000-\U0010FFFF]

# White Space
S ::= ( "\x20" | "\x09" | "\x0D" | "\x0A" )+

# Names and Tokens
NameStartChar ::= ":" | [A-Z] | "_" | [a-z] | [\xC0-\xD6] | [\xD8-\xF6] |
                  [\xF8-\u02FF]   | [\u0370-\u037D] | [\u037F-\u1FFF] |
                  [\u200C-\u2FEF] | [\u3001-\uD7FF] | [\uF900-\uFDCF] |
                  [\uFDF0-\uFFFD] | [\U00010000-\U000EFFFF]
NameChar ::= NameStartChar | "-" | "." | [0-9] | "\xB7" |
             [\u0300-\u036F] | [\u203F-\u2040]
Name ::= NameStartChar (NameChar)*
Names ::= Name ("\x20" Name)*
Nmtoken ::= (NameChar)+
Nmtokens ::= Nmtoken ("\x20" Nmtoken)*

# Literals
AttValue ::= ( "\x22" ([^<&\x22] | Reference)* "\x22" ) |
             ( "\x27" ([^<&\x27] | Reference)* "\x27" )

# Character Reference
CharRef ::= ("&#" [0-9]+ ";") | ("&#x" [0-9a-fA-F]+ ";")

# Entity Reference
Reference ::= EntityRef | CharRef
EntityRef ::= "&" Name ";"

# Character Data
CharData ::= (("]]" [^>]) | [^<&])*
"""
    )

    if allow_comments:
        misc.append("Comment")
        output_buffer.write(
            r"""
# Comments
commentChar ::= Char | [>?\x5F]
Comment ::= "<!--" (commentChar | ("-" commentChar))* "-->"
"""
        )

    if allow_pi:
        misc.append("PI")
        output_buffer.write(
            r"""
# Processing Instructions
piChar ::= Char | [\x2D\x5F]
PI ::= "<?" PITarget (S (("?" piChar) | (piChar | ">"))* )? "?>"
PITarget ::= ([^Xx] [^Mm] [^Ll]) | Name
"""
        )

    if allow_cdata:
        output_buffer.write(
            r"""
# CDATA Sections
cdChar ::= Char | [?\x2D]
CDSect ::= CDStart CData CDEnd
CDStart ::= "<![CDATA["
CData ::= ((Char | ">") | "]" (Char | ">" | ("]" Char)))*
CDEnd ::= "]]>"
"""
        )

    match xml_header:
        case Usage.REQUIRED:
            xml_decl = "XMLDecl Misc*"
        case Usage.ALLOWED:
            xml_decl = "XMLDecl? Misc*"
        case Usage.FORBIDDEN:
            xml_decl = "Misc*"

    match doctype:
        case Usage.REQUIRED:
            prolog = f"{xml_decl} doctypedecl Misc*"
        case Usage.ALLOWED:
            prolog = f"{xml_decl} (doctypedecl Misc*)?"
        case Usage.FORBIDDEN:
            prolog = xml_decl

    output_buffer.write(
        f"""
# Prolog
prolog ::= {prolog}
XMLDecl ::= "<?xml" VersionInfo EncodingDecl? SDDecl? S? "?>"
VersionInfo ::= S "version" Eq  ( ("\\x27" VersionNum "\\x27") |
                                  ("\\x22" VersionNum "\\x22") )
Eq ::= S? "=" S?
VersionNum ::= "1.0"
Misc ::= { " | ".join(misc) }

# Standalone Document Declaration
SDDecl ::= S "standalone" Eq ( ("\\x27" ("yes" | "no") "\\x27") |
                               ("\\x22" ("yes" | "no") "\\x22") )

# Encoding Declaration
EncodingDecl ::= S "encoding" Eq ("\\x22" EncName "\\x22" | "\\x27" EncName "\\x27")
EncName ::= [A-Z] | [a-z] ([A-Z] | [a-z] | [0-9] | [._] | "-")*

# Element Schema
"""
    )
    # TODO DTD (external and internal)

    for element in dtd.elements():
        if root_element is None:
            root_element = element.name
        ident = f"element-{_sanatize_ident(element.name)}"
        indent_len = len(ident) + 5
        output_buffer.write(f'{ident} ::= "<{element.name}" ')

        attributes = element.attributes()
        if len(attributes) > 0:
            output_buffer.write("(\n")
            for attribute in element.attributes():
                output_buffer.write(" " * (indent_len + 2))
                output_buffer.write(
                    f"(S {ident}-attribute-{_sanatize_ident(attribute.name)})"
                )
                if attribute.default != "required":
                    output_buffer.write("?")
                output_buffer.write("\n")
            output_buffer.write(" " * indent_len)
            output_buffer.write(") ")

        if element.type == "empty":
            output_buffer.write('S? "/>"\n')
        else:
            output_buffer.write('S? ">" (\n')
            new_group = element.content.type != "pcdata"
            _handle_element_content(
                allow_cdata,
                misc,
                output_buffer,
                element.content,
                indent_len + 2,
                new_group,
            )
            output_buffer.write("\n")
            output_buffer.write(" " * indent_len)
            output_buffer.write(f') "</{element.name}" S? ">"\n')

        for attribute in element.attributes():
            output_buffer.write(f"{ident}-attribute-{_sanatize_ident(attribute.name)}")
            output_buffer.write(' ::= "')
            output_buffer.write(attribute.name)
            output_buffer.write('" Eq AttValue\n')

    output_buffer.write(
        f"""
# Document Type Definition
doctypedecl ::= "<!DOCTYPE" S "{root_element}" S? ">"

root ::= prolog element-{_sanatize_ident(root_element)}
"""
    )


def _handle_cli():
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    parser.add_argument(
        "-i",
        "--input",
        type=argparse.FileType("r"),
        default="-",
        help="Input DTD file (default STDIN)",
        dest="dtd_pointer",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=argparse.FileType("w"),
        default="-",
        help="GBNF output location (default STDOUT)",
        dest="output_buffer",
    )
    parser.add_argument(
        "--allow-comments",
        action=argparse.BooleanOptionalAction,
        help="Whether to allow comments in the generated XML (default False)",
    )
    parser.add_argument(
        "--allow-pi",
        action=argparse.BooleanOptionalAction,
        help="Whether to allow XML processing instructions in the generated XML (default False)",
    )
    parser.add_argument(
        "--allow-cdata",
        action=argparse.BooleanOptionalAction,
        help="Whether to allow CData sections in the generated XML (default True)",
    )
    parser.add_argument(
        "--xml-header",
        type=str.upper,
        choices=["REQUIRED", "ALLOWED", "FORBIDDEN"],
        help="Whether to include an XML header in the generated XML (default ALLOWED)",
    )
    parser.add_argument(
        "--doctype",
        type=str.upper,
        choices=["REQUIRED", "ALLOWED", "FORBIDDEN"],
        help="Whether to include a DOCTYPE declaration in the generated XML (default REQUIRED)",
    )
    args = parser.parse_args()
    create_grammar(**vars(args))


if __name__ == "__main__":
    _handle_cli()
