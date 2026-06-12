import QtQuick
import QtQuick.Controls.Basic
import ".."

ScrollBar {
    id: control

    implicitWidth: 8
    implicitHeight: 8
    padding: 0
    hoverEnabled: true

    contentItem: Rectangle {
        implicitWidth: 8
        implicitHeight: 8
        radius: Theme.radius_small
        color: control.pressed || control.hovered ? Theme.scroll_handle_hover : Theme.scroll_handle
        opacity: control.policy === ScrollBar.AlwaysOn || (control.active && control.size < 1.0) ? 1.0 : 0.0
        Behavior on opacity { NumberAnimation { duration: 200 } }
        Behavior on color { ColorAnimation { duration: 150 } }
    }
}
