nextflow.enable.dsl=2

process SELECT {
    input:
    path source, name: 'source.pdb'
    path selection, name: 'selection.pdb'
    path settings, name: 'settings.json'
    path adapter, name: 'trp_select.py'
    output:
    path '0syn.pdb'
    script:
    '''
    python trp_select.py
    '''
    stub:
    '''
    cp selection.pdb 0syn.pdb
    '''
}

process GEOMETRY {
    publishDir 'results', mode: 'copy', overwrite: false
    input:
    path structure, name: '0syn.pdb'
    path settings, name: 'settings.json'
    path adapter, name: 'trp_geometry.py'
    output:
    path 'geometry.csv'
    script:
    '''
    python trp_geometry.py
    '''
    stub:
    '''
    echo 'STUB_ONLY_NO_SCIENTIFIC_RESULT' > geometry.csv
    '''
}

workflow {
    selected = SELECT(file('source.pdb', checkIfExists: true), file('selection.pdb', checkIfExists: true), file('settings.json', checkIfExists: true), file('trp_select.py', checkIfExists: true))
    GEOMETRY(selected, file('settings.json', checkIfExists: true), file('trp_geometry.py', checkIfExists: true))
}
