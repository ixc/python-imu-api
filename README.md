# python-imu-api

Provides a python interface to KE IMu that allows you to query and extract data. 

- [Installation](#installation)
- [Background](#background)
- [Documentation](#documentation)
- [Emu & Imu: lessons learnt & technical details](#emu--imu-lessons-learnt--technical-details)
- [Related projects & further reading](#development-notes)
- [Development notes](#development-notes)


## Installation

```
pip install imu-api
```


## Background

A number of galleries, museums, and other such institutions use the Emu system to manage their collections. 
The Emu system has a "module" Imu that the vendor can activate to expose an API for external consumption
of Emu's data.

Tasked with building a large web CMS that required collection data integration, we started to investigate and 
realised that Emu's vendor - Axiell, formerly KE Software - does provide some API wrappers. Unfortunately,
the documentation and source code only provide a very faint sense of how to interact with IMu. Additionally, at 
the time this library was built (2017), the wrappers were only provided in some older languages 
(VB, perl, Java, etc).

Our staff are largely python programmers, so we used wireshark to reverse-engineer the network payloads and   
and referenced the perl+php wrappers to implement a largely compatible library in Python. Note that while this 
wrapper has largely reached feature parity with the vendor's libs, we're unlikely to implement some of IMu's
quirks such as JSON binary transport.


## Documentation

### Create an Imu session

```python
from imu_api import imu_api

session = imu_api.create_imu_session(
    host="...",
    port="...",
    username="...",
    password="...",
)
```

The `create_imu_session` utility method will log your session in automatically as a connection test.

Note that for any automated code (periodic synching, etc), you may need to handle license exhaustion as Emu
systems are designed to limit login numbers to the amount of purchased licenses.


### Fetch data from every record in a module

```python
from imu_api import imu_api

session = ...

imu_table = imu_api.Module("ecatalogue", session)
imu_results = imu_table.find_terms(imu_api.Term())
results = imu_results.fetch_all(
    columns=(
        "irn",
        "TitMainTitle"
        "TitAccessionNo", 
        "CreCreatorRef_tab.irn",
    ),
    page_size=100,
)
```

This will query the work/catalogue module (`ecatalogue`) and fetch the irn, title, accession number and the irns of 
a record's creators. Records would be returned in a format similar to

```python
[
  {
    "irn": "...", 
    "TitMainTitle": "...",
    "TitAccessionNo": "...", 
    "CreCreatorRef_tab": [
      {"irn": "..."}
    ],
  },
  # ...
]
```

Note that `fetch_all` is a convenience method that handles pagination automatically.


### Query Emu data and fetch a single page of matching records

```python
from imu_api import imu_api

session = ...

imu_table = imu_api.Module("ecatalogue", session)
imu_terms = imu_api.Term(operator=imu_api.Term.OR_OPERATOR)
imu_terms.add("irn", 123)
imu_terms.add("irn", 234)
imu_results = imu_table.find_terms(imu_terms)
result_count = imu_results.data["result"]
fetched = imu_results.fetch(
    flag="current", 
    offset=0, 
    count=result_count, 
    columns=(
        "irn",
        "TitMainTitle",
    ),
)
fetched.data["result"]["rows"]
```

This will query the work/catalogue module (`ecatalogue`) and fetch the irn and title of the works that match 
have an irn matching `123` or `234`. Records would be returned in a format similar to

```python
{
  "result": {
    "rows": [
      {
        "irn": 123,
        "TitMainTitle": "...",
      },
      # ...
    ],
  },
}
```

If you want to spread your results across multiple pages, you can use the `offset` and `count` arguments to 
slice the results.


## Emu & Imu: lessons learnt & technical details

Emu is an old system with some eccentricities that reflect its legacy. Imu is a useful tool, providing you can 
get past the dozens of sharp edges and snake pits. The following are some hard learnt lessons that will hopefully
be of help:


### Reading the Emu Schema

As far as we can tell, there's no way to get a schema out of IMu or Emu. If you contact the vendor, they should be 
able to provide a "data dictionary" that breaks down all the modules and fields. Basically, a massive spreadsheet
with thousands of fields.

Note that the schema will list many fields that are inaccessible by Imu as it throws unknown field errors. In some 
cases, these fields appear to be inaccessible relational accessors - where the data actually lives in a related 
object. These fields may be accessible by consuming the related object with the source field on that object.


### Internal Reference Number (IRN)

Internally, EMu/IMu provide `irn` fields, which represent the Internal Reference Number. They are analogous to
primary keys and seem to be unique for modules/tables (but not necessarily for the system).


### Accessing relational data and fields

When searching or retrieving across a related field, you'll probably want to target something like `FooFieldRef`.
`...Ref` seems to be an id field for a single relation to a related module, analogous to a Foreign Key. Related 
fields can also act as an accessor to pluck nested fields with something like `FooFieldRef.BarField`. 

In some cases, the related fields will have an `...Ref_tab`, this seems to suggest a M2M relation or a list field. 
In these cases, the `FooFieldRef_tab` should return a list of the IRNs of the related instances. Similarly, the field can
can also act to pluck the related fields with something like `FooFieldRef_tab.BarField`.


### Imu socket transport

Imu's transport mechanism is a tad odd - they use a basic TCP socket to transport JSON payloads. This lib re-uses
the same `8192` block-size that the official Perl/PHP wrappers use. There's no message termination character,
so we have to check for the end of the JSON payload, which looks like `\n}\r\n`.


### Imu JSON parsing

For reasons that are not documented publicly, each of the IMu wrappers use their own hand-written JSON parsers. 
From poking around the Perl/PHP wrappers, we suspect that IMu uses a variant of JSON which allows them to send 
binary data down the wire (eg: thumbnails). We haven't replicated the binary handling as we have yet to need it.


### Imu JSON encoding

IMu doesn't do a great job of handling strings within JSON. It looks like they just concatenate them together when 
building JSON payloads (possibly necessary for their binary stuff). This has one big downside: they don't escape 
newlines or other control characters that are in the data.

We use python's `json` library, so Imu's unescaped newlines produced malformed JSON that would crashe our 
parser. Unfortunately, we've ended up needed to pre-process all incoming payloads and escape the characters 
manually. Once processed, then we can parse the payloads. Note that there's some test coverage on that part, but 
it's the part most likely to be tripped up by edge-cases in the data.


## Further reading

- IMU docs: http://imu.mel.kesoftware.com/doc/index.html
- Perl wrapper docs: http://imu.mel.kesoftware.com/doc/api/perl/index.html
- PHP wrapper docs: http://imu.mel.kesoftware.com/doc/api/php/index.html


## Related projects

- Official IMu Nodejs wrapper: https://github.com/axiell/imu-api-nodejs
- Official IMu Perl wrapper: https://github.com/axiell/imu-api-perl
- Official IMu PHP wrapper: https://github.com/axiell/imu-api-php
- Official IMu .NET wrapper: https://github.com/axiell/imu-api-dotnet
- Official IMu Java API: https://github.com/axiell/imu-api-java
- Alternative IMu PHP wrapper: https://github.com/fieldmuseum/BIMu


## Development notes


### Run tests

```
pip install -r requirements.txt
nosetests
```


### Formatting

```
pip install -r requirements.txt
black .
```
