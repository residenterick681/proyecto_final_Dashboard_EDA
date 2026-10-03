let
    Fuente = Csv.Document(Binary.FromText("QWN0aXZvLE5vbWJyZSxDYXRhbG9nb19mYWx0YW50ZSxFdGlxdWV0YQpBTSxBbWlzdGFkLDAsQU0gfCBBbWlzdGFkCkFQLEFwYWlrYSwwLEFQIHwgQXBhaWthCkFVLEF1Y2EsMCxBVSB8IEF1Y2EKQ1UsQ3V5YWJlbm8sMCxDVSB8IEN1eWFiZW5vCkVZLEVkw6luIFl1dHVyaSwwLEVZIHwgRWTDqW4gWXV0dXJpCklOLEluZGlsbGFuYSwwLElOIHwgSW5kaWxsYW5hCklUVCxJc2hwaW5nby1UaXB1dGluaS1UYW1ib2NvY2hhLDAsSVRUIHwgSXNocGluZ28tVGlwdXRpbmktVGFtYm9jb2NoYQpMQSxMYWdvIEFncmlvLDAsTEEgfCBMYWdvIEFncmlvCkxJLExpYmVydGFkb3IsMCxMSSB8IExpYmVydGFkb3IKT1ksT3NvIFl1cmFscGEsMCxPWSB8IE9zbyBZdXJhbHBhClBBLFBhbG8gQXp1bCwwLFBBIHwgUGFsbyBBenVsClNBLFNhY2hhLDAsU0EgfCBTYWNoYQpTSCxTaHVzaHVmaW5kaSwwLFNIIHwgU2h1c2h1ZmluZGkKQUIxNixBQjE2IChzaW4gY2F0w6Fsb2dvKSwxLEFCMTYgfCBBQjE2IChzaW4gY2F0w6Fsb2dvKQpBVixBbWF6b25pYSBWaXZhLDAsQVYgfCBBbWF6b25pYSBWaXZhCkFJVCxBbW8tSXJvLVRpdmFjdW5vLDAsQUlUIHwgQW1vLUlyby1UaXZhY3Vubwo=", BinaryEncoding.Base64), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Fuente, [PromoteAllScalars=true]),
    Nulos = Table.ReplaceValue(Encabezados, "", null, Replacer.ReplaceValue, Table.ColumnNames(Encabezados)),
    Tipos = Table.TransformColumnTypes(Nulos, {{"Activo", type text}, {"Nombre", type text}, {"Catalogo_faltante", Int64.Type}, {"Etiqueta", type text}}, "en-US")
in
    Tipos
