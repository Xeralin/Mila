import QtQuick
import QtQuick.Controls.Basic

DialogButtonBox {
    id: control

    alignment: Qt.AlignRight
    spacing: 8
    leftPadding: 20
    rightPadding: 20
    topPadding: 8
    bottomPadding: 20
    background: null
    delegate: MilaButton {}
}
