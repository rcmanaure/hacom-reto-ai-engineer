# Genera HACOM-Reto-AI-Engineer.docx y .pdf desde documento-tecnico.md.
# Requiere uv y Microsoft Word (se usa por COM para dar formato y exportar a PDF).
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

uv run --python 3.13 --with pypandoc_binary python -c "import pypandoc; pypandoc.convert_file('documento-tecnico.md','docx',outputfile='HACOM-Reto-AI-Engineer.docx',extra_args=['--toc','--toc-depth=2','--resource-path=.'])"
if ($LASTEXITCODE -ne 0) { throw "pandoc falló" }

$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $doc = $word.Documents.Open("$PSScriptRoot\HACOM-Reto-AI-Engineer.docx")

    foreach ($t in $doc.Tables) {
        $t.Borders.Enable = 1
        $t.Range.Font.Size = 9
        $t.AutoFitBehavior(2)                                 # ajustar al ancho de página
        $t.Rows.AllowBreakAcrossPages = 0                     # una fila no se parte entre páginas
        $header = $t.Rows.Item(1)
        $header.Range.Font.Bold = 1
        $header.Shading.BackgroundPatternColor = 15132390     # gris claro
        $header.HeadingFormat = -1                            # repetir encabezado en cada página
        $header.Range.ParagraphFormat.KeepWithNext = -1       # no dejar el encabezado solo al pie
    }

    # Diagramas apaisados (lógico) en una página horizontal y muy altos (estados) en una página propia.
    # De atrás hacia adelante para no mover las posiciones de las imágenes anteriores.
    for ($i = $doc.InlineShapes.Count; $i -ge 1; $i--) {
        $shape = $doc.InlineShapes.Item($i)
        $aspecto = $shape.Width / $shape.Height
        if ($aspecto -ge 0.6 -and $aspecto -lt 1.4) { continue }
        $img = $shape.Range.Paragraphs.Item(1).Range
        $caption = $img.Next(4, 1)                            # wdParagraph: la leyenda de la figura
        $start = $img.Start
        $prev = $img.Previous(4, 1)
        if ($prev.ParagraphFormat.OutlineLevel -lt 10) { $start = $prev.Start }   # el título viaja con su diagrama
        $doc.Range($caption.End, $caption.End).InsertBreak(2) # wdSectionBreakNextPage
        $doc.Range($start, $start).InsertBreak(2)
        if ($aspecto -ge 1.4) { $shape.Range.Sections.Item(1).PageSetup.Orientation = 1 }   # wdOrientLandscape
    }

    foreach ($s in $doc.Sections) {
        $s.PageSetup.LeftMargin = 50
        $s.PageSetup.RightMargin = 50
    }

    foreach ($shape in $doc.InlineShapes) {
        $ps = $shape.Range.Sections.Item(1).PageSetup
        $reserva = 90                                          # lugar para título y leyenda
        if ($shape.Width / $shape.Height -lt 0.6) {            # página propia: márgenes mínimos y solo la leyenda
            $ps.TopMargin = 30; $ps.BottomMargin = 30; $ps.LeftMargin = 30; $ps.RightMargin = 30
            $reserva = 35
        }
        $maxW = $ps.PageWidth - $ps.LeftMargin - $ps.RightMargin
        $maxH = $ps.PageHeight - $ps.TopMargin - $ps.BottomMargin - $reserva
        $shape.LockAspectRatio = -1
        $factor = [Math]::Min($maxW / $shape.Width, $maxH / $shape.Height)   # agranda o achica hasta llenar el espacio
        $shape.Width = $shape.Width * $factor
    }

    $doc.Save()
    $doc.SaveAs2("$PSScriptRoot\HACOM-Reto-AI-Engineer.pdf", 17)   # wdFormatPDF
    $doc.Close()
}
finally {
    $word.Quit()
}
