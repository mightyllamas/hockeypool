function isFloatColumn( colName ) {
    return colName == "PPG" || colName == "GAA" || colName == "Sv%";
}
function salaryFormat( e1, oRecord, oColumn, oData ) {
    e1.innerHTML = YAHOO.util.Number.format( oData, {prefix:"", decimalPlaces:0, thousandsSeparator:","} );
}
function fixedDigitFormat( numDigits ) {
    return function ( e1, oRecord, oColumn, oData ) {
        e1.innerHTML = YAHOO.util.Number.format( oData, {decimalPlaces:numDigits} );
    }
}
function formatDelta( e1, oRecord, oColumn, oData ) {
    if( oColumn.key == 'dtp' || oColumn.key == 'dPC' || oColumn.key == 'pdtp' ) {
        e1.innerHTML = YAHOO.util.Number.format( oData, {decimalPlaces:1} );
    } else if( isFloatColumn( oColumn.key.slice(1) ) ) {
        e1.innerHTML = YAHOO.util.Number.format( oData, {decimalPlaces:2} );
    } else {
        e1.innerHTML = YAHOO.util.Number.format( oData );
    }
    if( oColumn.key == 'dGAA' ) oData = oData * -1
    if( oData < 0 ) {
        e1.innerHTML = "<div class=\"negative\">" + e1.innerHTML + "</div>"
    } else if( oData > 0 ) {
        e1.innerHTML = "<div class=\"positive\">" + e1.innerHTML + "</div>"
    }
}
