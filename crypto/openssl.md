# OpenSSL and checksums

## Generate sha256 for a file

```bash
openssl sha256 -hex -out [outputfile.sha256] [filetochecksum]
```

## view checksum of sha256

```bash
cat [file.sha256]
```

## view checksum of file

```bash
sha256sum [filetochecksum]
```

```bash
pemba@pt22:/Github$ openssl sha256 -hex -out scratch.sha256 scratch.ipynb 
pemba@pt22:/Github$ cat scratch.sha256 

>>> SHA256(scratch.ipynb)= 2b561c10757c2b9aad46b47d3df2632e11bd47e9fffd6be9c75f36df4027f651

pemba@pt22:/Github$ sha256sum scratch.ipynb 

>>> 2b561c10757c2b9aad46b47d3df2632e11bd47e9fffd6be9c75f36df4027f651  scratch.ipynb
```
