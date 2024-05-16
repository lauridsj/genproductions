"""
This script reads in a LHE file and replaces the XWGTUP (generator weight)
of each event by the first weight found in the <weights> tag.
This is neccessary for bb4l since several features (including virtual corrections)
are only included in the reweighting for speed.

Author: Laurids Jeppe (laurids.jeppe@cern.ch)
"""

import argparse
import re

# Regex for finding multiple whitespaces
_RE_COMBINE_WHITESPACE = re.compile(r"\s+")

parser = argparse.ArgumentParser()
parser.add_argument("lhefile")
parser.add_argument("--verbose", "-v", action="store_true")
args = parser.parse_args()

inpath = args.lhefile
outpath = args.lhefile.split(".lhe")[0] + "_weighted.lhe"

infile = open(inpath, "r")
outfile = open(outpath, "w")

num_events = 0
in_event = False
in_weights = False
virtual_weight = None
current_event = []
# Loop over all lines in the input file
while True:
    try:
        line = infile.readline()
    except EOFError:
        break
    if not line:
        break

    # Detect whether we are in an <event> block
    if line.startswith("<event>"):
        in_event = True
        # Reset all variables
        in_weights = False
        virtual_weight = None
        current_event = []
        num_events += 1

    if in_event:
        append = True
        if line.startswith("</event>"):
            if in_weights:
                raise ValueError("</event> tag before </weights> tag")
            in_event = False

        elif line.startswith("</weights>") or line.startswith("</rwgt>"):
            in_weights = False
            
        elif line.startswith("<weights>") or line.startswith("<rwgt>"):
            in_weights = True

        elif in_weights:
            if virtual_weight is None:
                # First weight - this is the one 
                # we want to normalize the others to
                # so we cache it
                virtual_weight = line.strip()
                # There are two possible ways for powheg to store the weights
                # either with the <wgt> tag or as plain numbers
                # in the first case we need to extract the weight
                # in the latter case we dont need to do anything
                if virtual_weight.startswith("<wgt"):
                    if not "</wgt>" in virtual_weight:
                        raise ValueError("Event {:}: Malformed line: {:}".format(num_events, virtual_weight))
                    # Take the content of the tag (between <wgt id=...> and </wgt>)
                    virtual_weight = virtual_weight.split(">")[1]
                    virtual_weight = virtual_weight.split("<")[0]
                    virtual_weight = virtual_weight.strip()

        current_event.append(line)

        if not in_event:

            # Make sure that a virtual weight was read in the event
            if virtual_weight is None:
                raise ValueError("Event {:}: No virtual weight found in event!".format(num_events))

            # Rescale XWGTUP (i.e. the generator weight)
            # It is the third entry in the second line
            # (the first line is just the <event> tag)
            eventinfo = current_event[1]
            # Remove additional whitespaces for the parsing
            eventinfo = _RE_COMBINE_WHITESPACE.sub(" ", eventinfo).strip()
            eventinfo_split = eventinfo.split(" ")

            if args.verbose:
                xwgtup_old = eventinfo_split[2]
                print("Event {:}: replacing XWGTUP of {:} by {:}".format(num_events, xwgtup_old, virtual_weight))

            # Undo the splitting again and replace the changed line
            eventinfo_split[2] = virtual_weight
            eventinfo = " ".join(eventinfo_split) + "\n"
            current_event[1] = eventinfo

            # Write the cached event to the output file
            outfile.writelines(current_event)

    else:
        # Lines outside of the <event> block (i.e. the header) just get copied
        outfile.write(line)

outfile.close()
infile.close()