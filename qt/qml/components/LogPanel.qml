import QtQuick
import QtQuick.Controls.Basic
import ".."

Rectangle {
    id: panel

    property alias text: area.text

    function append(line) {
        area.append(line)
    }

    color: Theme.log_background
    radius: Theme.radius
    border.width: 1
    border.color: Theme.hairline

    ScrollView {
        anchors.fill: parent
        anchors.margins: 12
        clip: true
        ScrollBar.vertical: MilaScrollBar {}
        ScrollBar.horizontal: MilaScrollBar {}

        TextArea {
            id: area
            readOnly: true
            wrapMode: TextArea.NoWrap
            color: Theme.text_log
            selectionColor: Theme.accent
            selectedTextColor: Theme.text_primary
            font.family: "monospace"
            font.pixelSize: Theme.font_small
            background: null
        }
    }
}
