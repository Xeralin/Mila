import QtQuick
import QtQuick.Controls.Basic
import ".."

TextField {
    id: control

    implicitHeight: Theme.control_height
    leftPadding: 12
    rightPadding: 12
    color: Theme.text_primary
    placeholderTextColor: Theme.text_placeholder
    selectionColor: Theme.accent
    selectedTextColor: Theme.text_primary
    selectByMouse: true
    verticalAlignment: TextInput.AlignVCenter
    font.pixelSize: Theme.font_body

    background: Rectangle {
        implicitWidth: 200
        implicitHeight: Theme.control_height
        radius: Theme.radius_small
        color: Theme.field
        border.width: 1
        border.color: control.activeFocus ? Theme.accent : Theme.border
        Behavior on border.color { ColorAnimation { duration: 150 } }
    }
}
